import shutil
from pathlib import Path

import click

from workstack.cli.commands.switch import complete_worktree_names
from workstack.cli.core import (
    discover_repo_context,
    ensure_workstacks_dir,
    validate_worktree_name_for_removal,
    worktree_path_for,
)
from workstack.core.context import WorkstackContext, create_context
from workstack.core.gitops import GitOps
from workstack.core.graphite_ops import read_graphite_json_file


def _try_git_worktree_remove(git_ops: GitOps, repo_root: Path, wt_path: Path) -> bool:
    """Attempt git worktree remove, returning success status.

    This function violates LBYL norms because there's no reliable way to
    check a priori if git worktree remove will succeed. The worktree might be:
    - Already removed from git metadata
    - In a partially corrupted state
    - Referenced by stale lock files

    Git's own error handling is unreliable for these edge cases, so we use
    try/except as an error boundary and rely on manual cleanup + prune.

    Returns:
        True if git removal succeeded, False otherwise
    """
    try:
        git_ops.remove_worktree(repo_root, wt_path, force=True)
        return True
    except Exception:
        # Git removal failed - manual cleanup will handle it
        return False


def _prune_worktrees_safe(git_ops: GitOps, repo_root: Path) -> None:
    """Prune worktree metadata, ignoring errors if nothing to prune.

    This function violates LBYL norms because git worktree prune can fail
    for various reasons (no stale worktrees, permission issues, etc.) that
    are not easily detectable beforehand. Since pruning is a cleanup operation
    and failure doesn't affect the primary operation, we allow silent failure.
    """
    try:
        git_ops.prune_worktrees(repo_root)
    except Exception:
        # Prune might fail if there's nothing to prune or other non-critical issues
        pass


def _find_worktree_branch(ctx: WorkstackContext, repo_root: Path, wt_path: Path) -> str | None:
    """Find the branch for a given worktree path.

    Returns None if worktree is not found or is in detached HEAD state.
    """
    worktrees = ctx.git_ops.list_worktrees(repo_root)
    for wt in worktrees:
        if wt.path == wt_path:
            return wt.branch
    return None


def _get_non_trunk_branches(ctx: WorkstackContext, repo_root: Path, stack: list[str]) -> list[str]:
    """Filter out trunk branches from a stack.

    Raises:
        ValueError: If git directory cannot be found
        FileNotFoundError: If Graphite cache is missing
        OSError: If cache cannot be read
        json.JSONDecodeError: If cache is invalid JSON
    """
    git_dir = ctx.git_ops.get_git_common_dir(repo_root)
    if git_dir is None:
        raise ValueError("Could not find git directory")

    cache_file = git_dir / ".graphite_cache_persist"
    if not cache_file.exists():
        raise FileNotFoundError(f"Graphite cache not found: {cache_file}")

    cache_data = read_graphite_json_file(cache_file, "Graphite cache")

    branches_data = cache_data.get("branches", [])

    trunk_branches = {
        branch_name
        for branch_name, info in branches_data
        if info.get("validationResult") == "TRUNK"
    }

    return [b for b in stack if b not in trunk_branches]


def _remove_worktree(
    ctx: WorkstackContext, name: str, force: bool, delete_stack: bool, dry_run: bool
) -> None:
    """Internal function to remove a worktree.

    Uses git worktree remove when possible, but falls back to direct rmtree
    if git fails (e.g., worktree already removed from git metadata but directory exists).
    This is acceptable exception handling because there's no reliable way to check
    a priori if git worktree remove will succeed - the worktree might be in various
    states of partial removal.

    Args:
        ctx: Workstack context with git operations
        name: Name of the worktree to remove
        force: Skip confirmation prompts
        delete_stack: Delete all branches in the Graphite stack (requires Graphite)
        dry_run: Print what would be done without executing destructive operations
    """
    # Create dry-run context if needed
    if dry_run:
        ctx = create_context(dry_run=True)

    # Validate worktree name before any operations
    validate_worktree_name_for_removal(name)

    repo = discover_repo_context(ctx, Path.cwd())
    workstacks_dir = ensure_workstacks_dir(repo)
    wt_path = worktree_path_for(workstacks_dir, name)

    if not wt_path.exists() or not wt_path.is_dir():
        click.echo(f"Worktree not found: {wt_path}")
        raise SystemExit(1)

    # Step 1: Collect all operations to perform
    branches_to_delete: list[str] = []
    if delete_stack:
        use_graphite = ctx.global_config_ops.get_use_graphite()
        if not use_graphite:
            click.echo(
                "Error: --delete-stack requires Graphite to be enabled. "
                "Run 'workstack config set use-graphite true'",
                err=True,
            )
            raise SystemExit(1)

        # Get the branches in the stack before removing the worktree
        worktrees = ctx.git_ops.list_worktrees(repo.root)
        worktree_branch = None
        for wt in worktrees:
            if wt.path == wt_path:
                worktree_branch = wt.branch
                break

        if worktree_branch is None:
            click.echo(
                f"Warning: Worktree {name} is in detached HEAD state. "
                "Cannot delete stack without a branch.",
                err=True,
            )
        else:
            stack = ctx.graphite_ops.get_branch_stack(ctx.git_ops, repo.root, worktree_branch)
            if stack is None:
                click.echo(
                    f"Warning: Branch {worktree_branch} is not tracked by Graphite. "
                    "Cannot delete stack.",
                    err=True,
                )
            else:
                branches_to_delete = _get_non_trunk_branches(ctx, repo.root, stack)

                if not branches_to_delete:
                    click.echo("No branches to delete (all branches in stack are trunk branches).")

    # Step 2: Display all planned operations
    if branches_to_delete or True:
        click.echo(click.style("📋 Planning to perform the following operations:", bold=True))
        worktree_text = click.style(str(wt_path), fg="cyan")
        click.echo(f"  1. 🗑️  Remove worktree: {worktree_text}")
        if branches_to_delete:
            click.echo("  2. 🌳 Delete branches in stack:")
            for branch in branches_to_delete:
                branch_text = click.style(branch, fg="yellow")
                click.echo(f"     - {branch_text}")

    # Step 3: Single confirmation prompt (unless --force or --dry-run)
    if not force and not dry_run:
        prompt_text = click.style("Proceed with these operations?", fg="yellow", bold=True)
        if not click.confirm(f"\n{prompt_text}", default=False):
            click.echo(click.style("⭕ Aborted.", fg="red", bold=True))
            return

    # Step 4: Execute operations

    # 4a. Try to remove via git first
    # This updates git's metadata when possible
    _try_git_worktree_remove(ctx.git_ops, repo.root, wt_path)

    # 4b. Always manually delete directory if it still exists
    # (git worktree remove may have succeeded or failed, but directory might still be there)
    if wt_path.exists():
        if ctx.dry_run:
            click.echo(f"[DRY RUN] Would delete directory: {wt_path}", err=True)
        else:
            shutil.rmtree(wt_path)

    # 4c. Prune worktree metadata to clean up any stale references
    # This is important if git worktree remove failed or if we manually deleted
    if not ctx.dry_run:
        _prune_worktrees_safe(ctx.git_ops, repo.root)

    # 4c. Delete stack branches (now that worktree is removed)
    if branches_to_delete:
        for branch in branches_to_delete:
            ctx.git_ops.delete_branch_with_graphite(repo.root, branch, force=force)
            if not dry_run:
                branch_text = click.style(branch, fg="green")
                click.echo(f"✅ Deleted branch: {branch_text}")

    if not dry_run:
        path_text = click.style(str(wt_path), fg="green")
        click.echo(f"✅ {path_text}")


@click.command("remove")
@click.argument("name", metavar="NAME", shell_complete=complete_worktree_names)
@click.option("-f", "--force", is_flag=True, help="Do not prompt for confirmation.")
@click.option(
    "-s",
    "--delete-stack",
    is_flag=True,
    help="Delete all branches in the Graphite stack (requires Graphite).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    # dry_run=False: Allow destructive operations by default
    default=False,
    help="Print what would be done without executing destructive operations.",
)
@click.pass_obj
def remove_cmd(
    ctx: WorkstackContext, name: str, force: bool, delete_stack: bool, dry_run: bool
) -> None:
    """Remove the worktree directory (alias: rm).

    With `-f/--force`, skips the confirmation prompt.
    Attempts `git worktree remove` before deleting the directory.
    """
    _remove_worktree(ctx, name, force, delete_stack, dry_run)


# Register rm as a hidden alias (won't show in help)
@click.command("rm", hidden=True)
@click.argument("name", metavar="NAME", shell_complete=complete_worktree_names)
@click.option("-f", "--force", is_flag=True, help="Do not prompt for confirmation.")
@click.option(
    "-s",
    "--delete-stack",
    is_flag=True,
    help="Delete all branches in the Graphite stack (requires Graphite).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    # dry_run=False: Allow destructive operations by default
    default=False,
    help="Print what would be done without executing destructive operations.",
)
@click.pass_obj
def rm_cmd(
    ctx: WorkstackContext, name: str, force: bool, delete_stack: bool, dry_run: bool
) -> None:
    """Remove the worktree directory (alias of 'remove')."""
    _remove_worktree(ctx, name, force, delete_stack, dry_run)
