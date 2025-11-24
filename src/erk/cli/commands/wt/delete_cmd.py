import shutil
import subprocess
from pathlib import Path

import click
from erk_shared.git.abc import Git

from erk.cli.commands.completions import complete_worktree_names
from erk.cli.core import (
    discover_repo_context,
    validate_worktree_name_for_deletion,
    worktree_path_for,
)
from erk.cli.ensure import Ensure
from erk.cli.output import user_output
from erk.core.context import ErkContext, create_context, regenerate_context
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.core.worktree_utils import (
    filter_non_trunk_branches,
    find_worktree_containing_path,
    get_worktree_branch,
)


def _try_git_worktree_delete(git_ops: Git, repo_root: Path, wt_path: Path) -> bool:
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


def _prune_worktrees_safe(git_ops: Git, repo_root: Path) -> None:
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


def _delete_worktree(
    ctx: ErkContext,
    name: str,
    force: bool,
    delete_stack: bool,
    dry_run: bool,
    quiet: bool = False,
) -> None:
    """Internal function to delete a worktree.

    Uses git worktree remove when possible, but falls back to direct rmtree
    if git fails (e.g., worktree already deleted from git metadata but directory exists).
    This is acceptable exception handling because there's no reliable way to check
    a priori if git worktree remove will succeed - the worktree might be in various
    states of partial deletion.

    Args:
        ctx: Erk context with git operations
        name: Name of the worktree to delete
        force: Skip confirmation prompts
        delete_stack: Delete all branches in the Graphite stack (requires Graphite)
        dry_run: Print what would be done without executing destructive operations
        quiet: Suppress planning output (still shows final confirmation)
    """
    # Create dry-run context if needed
    if dry_run:
        ctx = create_context(dry_run=True)

    # Validate worktree name before any operations
    validate_worktree_name_for_deletion(name)

    # Use ctx.cwd which is kept up-to-date by regenerate_context() after directory changes.
    # In pure test mode, ctx.cwd is a sentinel path; in production, it's updated
    # by regenerate_context() to match the actual OS cwd after safe_chdir() calls.
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    wt_path = worktree_path_for(repo.worktrees_dir, name)

    # Check if worktree exists using git operations (works with both real and sentinel paths)
    Ensure.path_exists(ctx, wt_path, f"Worktree not found: {wt_path}")

    # LBYL: Check if user is currently in the worktree being deleted
    # If so, change to repository root before deletion to prevent
    # shell from being in deleted directory
    if ctx.git.path_exists(ctx.cwd):
        current_dir = ctx.cwd.resolve()
        worktrees = ctx.git.list_worktrees(repo.root)
        current_worktree_path = find_worktree_containing_path(worktrees, current_dir)

        if (
            current_worktree_path is not None
            and current_worktree_path.resolve() == wt_path.resolve()
        ):
            # Change to repository root before deletion
            safe_dir = repo.root
            user_output(
                click.style("ℹ️  ", fg="blue", bold=True)
                + f"Changing directory to repository root: {click.style(str(safe_dir), fg='cyan')}"
            )

            # Change directory using safe_chdir which handles both real and sentinel paths
            if not dry_run and ctx.git.safe_chdir(safe_dir):
                # Regenerate context with new cwd (context is immutable)
                ctx = regenerate_context(ctx)

    # Step 1: Collect all operations to perform
    branches_to_delete: list[str] = []
    if delete_stack:
        use_graphite = ctx.global_config.use_graphite if ctx.global_config else False
        if not use_graphite:
            user_output(
                "Error: --delete-stack requires Graphite to be enabled. "
                "Run 'erk config set use_graphite true'",
            )
            raise SystemExit(1)

        # Get the branches in the stack before deleting the worktree
        worktrees = ctx.git.list_worktrees(repo.root)
        worktree_branch = get_worktree_branch(worktrees, wt_path)

        if worktree_branch is None:
            user_output(
                f"Warning: Worktree {name} is in detached HEAD state. "
                "Cannot delete stack without a branch.",
            )
        else:
            stack = ctx.graphite.get_branch_stack(ctx.git, repo.root, worktree_branch)
            if stack is None:
                user_output(
                    f"Warning: Branch {worktree_branch} is not tracked by Graphite. "
                    "Cannot delete stack.",
                )
            else:
                # Get all branches and filter to non-trunk branches
                all_branches = ctx.graphite.get_all_branches(ctx.git, repo.root)
                if not all_branches:
                    raise ValueError("Graphite cache not available")
                branches_to_delete = filter_non_trunk_branches(all_branches, stack)

                if not branches_to_delete:
                    user_output("No branches to delete (all branches in stack are trunk branches).")

    # Step 2: Display all planned operations
    if not quiet:  # Only show planning if not in quiet mode
        if branches_to_delete or True:
            user_output(click.style("📋 Planning to perform the following operations:", bold=True))
            worktree_text = click.style(str(wt_path), fg="cyan")
            user_output(f"  1. 🗑️  Delete worktree: {worktree_text}")
            if branches_to_delete:
                user_output("  2. 🌳 Delete branches in stack:")
                for branch in branches_to_delete:
                    branch_text = click.style(branch, fg="yellow")
                    user_output(f"     - {branch_text}")

    # Step 3: Single confirmation prompt (unless --force or --dry-run)
    if not force and not dry_run:
        prompt_text = click.style("Proceed with these operations?", fg="yellow", bold=True)
        if not click.confirm(f"\n{prompt_text}", default=False):
            user_output(click.style("⭕ Aborted.", fg="red", bold=True))
            return

    # Step 4: Execute operations

    # 4a. Try to delete via git first
    # This updates git's metadata when possible
    _try_git_worktree_delete(ctx.git, repo.root, wt_path)

    # 4b. Always manually delete directory if it still exists
    # (git worktree remove may have succeeded or failed, but directory might still be there)
    # Use git_ops.path_exists() instead of .exists() to work with both real and sentinel paths
    if ctx.git.path_exists(wt_path):
        if ctx.dry_run:
            user_output(f"[DRY RUN] Would delete directory: {wt_path}")
        else:
            # Only call shutil.rmtree() if we're on a real filesystem
            # In pure test mode, we skip the actual deletion since it's a sentinel path
            try:
                shutil.rmtree(wt_path)
            except OSError:
                # Path doesn't exist on real filesystem (sentinel path), skip deletion
                pass

    # 4c. Prune worktree metadata to clean up any stale references
    # This is important if git worktree remove failed or if we manually deleted
    # Trust DryRunGit wrapper to handle dry-run behavior
    _prune_worktrees_safe(ctx.git, repo.root)

    # 4c. Delete stack branches (now that worktree is removed)
    # Exception handling here is acceptable because:
    # 1. gt delete prompts for user confirmation, which can be declined (exit 1)
    # 2. There's no LBYL way to predict user's response to interactive prompt
    # 3. This is a CLI error boundary - appropriate place per AGENTS.md
    if branches_to_delete:
        for branch in branches_to_delete:
            try:
                ctx.git.delete_branch_with_graphite(repo.root, branch, force=force)
                if not dry_run:
                    branch_text = click.style(branch, fg="green")
                    user_output(f"✅ Deleted branch: {branch_text}")
            except subprocess.CalledProcessError as e:
                # User declined deletion or branch doesn't exist
                # Exit code 1 typically means user said "no" to confirmation prompt
                branch_text = click.style(branch, fg="yellow")
                if e.returncode == 1 and not force:
                    # User declined - this is expected behavior, not an error
                    user_output(
                        f"⭕ Skipped deletion of branch: {branch_text} "
                        f"(user declined or not eligible)"
                    )
                    user_output("Remaining branches in stack were not deleted.")
                    break  # Stop processing remaining branches
                else:
                    # Other error (branch doesn't exist, git failure, etc.)
                    error_detail = e.stderr.strip() if e.stderr else f"exit code {e.returncode}"
                    user_output(
                        click.style("Error: ", fg="red")
                        + f"Failed to delete branch {branch_text}: {error_detail}"
                    )
                    raise SystemExit(1) from e
            except FileNotFoundError:
                # gt command not found
                user_output(
                    click.style("Error: ", fg="red")
                    + "'gt' command not found. Install Graphite CLI: "
                    "brew install withgraphite/tap/graphite"
                )
                raise SystemExit(1) from None

    if not dry_run:
        path_text = click.style(str(wt_path), fg="green")
        user_output(f"✅ {path_text}")


@click.command("delete")
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
def delete_wt(ctx: ErkContext, name: str, force: bool, delete_stack: bool, dry_run: bool) -> None:
    """Delete the worktree directory (alias: del).

    With `-f/--force`, skips the confirmation prompt.
    Attempts `git worktree remove` before deleting the directory.
    """
    _delete_worktree(ctx, name, force, delete_stack, dry_run)


# Register del as a hidden alias (won't show in help)
@click.command("del", hidden=True)
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
def del_wt(ctx: ErkContext, name: str, force: bool, delete_stack: bool, dry_run: bool) -> None:
    """Delete the worktree directory (alias of 'delete')."""
    _delete_worktree(ctx, name, force, delete_stack, dry_run)
