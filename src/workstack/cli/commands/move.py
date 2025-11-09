"""Move branches between worktrees with explicit source specification."""

from pathlib import Path

import click

from workstack.cli.commands.switch import complete_worktree_names
from workstack.cli.core import discover_repo_context, ensure_workstacks_dir, worktree_path_for
from workstack.core.context import WorkstackContext


def _get_worktree_branch(ctx: WorkstackContext, repo_root: Path, wt_path: Path) -> str | None:
    """Get the branch checked out in a worktree.

    Returns None if worktree is not found or is in detached HEAD state.
    """
    worktrees = ctx.git_ops.list_worktrees(repo_root)
    # Resolve paths for comparison to handle relative vs absolute paths
    wt_path_resolved = wt_path.resolve()
    for wt in worktrees:
        if wt.path.resolve() == wt_path_resolved:
            return wt.branch
    return None


def _find_worktree_containing_path(worktrees: list, target_path: Path) -> Path | None:
    """Find which worktree contains the given path.

    Args:
        worktrees: List of WorktreeInfo objects
        target_path: Path to check (should be resolved)

    Returns:
        Path to the worktree that contains target_path, or None if not found

    Note:
        Uses is_relative_to() to check path containment. This is the LBYL approach
        (vs catching ValueError from relative_to()).

        Returns the most specific (longest) match to handle nested worktrees.
        For example, if target_path is /a/b/c and we have worktrees at /a and /a/b,
        this returns /a/b (the more specific match).
    """
    best_match: Path | None = None
    best_match_depth = -1

    for wt in worktrees:
        wt_path = wt.path.resolve()
        # Check if target_path is within this worktree
        # is_relative_to() returns True if target_path is under wt_path
        if target_path.is_relative_to(wt_path):
            # Count path depth to find most specific match
            depth = len(wt_path.parts)
            if depth > best_match_depth:
                best_match = wt_path
                best_match_depth = depth

    return best_match


def _find_worktree_with_branch(ctx: WorkstackContext, repo_root: Path, branch: str) -> Path | None:
    """Find the worktree path containing the specified branch.

    Returns None if the branch is not found in any worktree.
    """
    worktrees = ctx.git_ops.list_worktrees(repo_root)
    for wt in worktrees:
        if wt.branch == branch:
            return wt.path
    return None


def _resolve_current_worktree(ctx: WorkstackContext, repo_root: Path) -> Path:
    """Find worktree containing current directory.

    Raises SystemExit if not in a git repository or not in any worktree.
    """
    git_common_dir = ctx.git_ops.get_git_common_dir(ctx.cwd)
    if git_common_dir is None:
        click.echo("Error: Not in a git repository", err=True)
        raise SystemExit(1)

    cwd = ctx.cwd.resolve()
    worktrees = ctx.git_ops.list_worktrees(repo_root)
    wt_path = _find_worktree_containing_path(worktrees, cwd)
    if wt_path is None:
        click.echo(
            f"Error: Current directory ({cwd}) is not in any worktree.\n"
            f"Either run this from within a worktree, or use --worktree or "
            f"--branch to specify the source.",
            err=True,
        )
        raise SystemExit(1)
    return wt_path


def resolve_source_worktree(
    ctx: WorkstackContext,
    repo_root: Path,
    *,
    current: bool,
    branch: str | None,
    worktree: str | None,
    workstacks_dir: Path,
) -> Path:
    """Determine source worktree from flags.

    Defaults to current worktree if no flags provided.
    Raises SystemExit if multiple flags specified or if source cannot be resolved.
    """
    # Count how many source flags are specified
    flag_count = sum([current, branch is not None, worktree is not None])

    if flag_count > 1:
        click.echo(
            "Error: Only one of --current, --branch, or --worktree can be specified", err=True
        )
        raise SystemExit(1)

    if flag_count == 0 or current:
        # Default to current worktree (either no flags or --current explicitly set)
        return _resolve_current_worktree(ctx, repo_root)

    if branch:
        # Find worktree containing this branch
        wt = _find_worktree_with_branch(ctx, repo_root, branch)
        if wt is None:
            click.echo(f"Error: Branch '{branch}' not found in any worktree", err=True)
            raise SystemExit(1)
        return wt

    if worktree:
        # Resolve worktree name to path
        wt_path = worktree_path_for(workstacks_dir, worktree)
        # Validate that the worktree exists
        if not wt_path.exists():
            click.echo(f"Error: Worktree '{worktree}' does not exist", err=True)
            raise SystemExit(1)
        return wt_path

    click.echo("Error: Invalid state - no source specified", err=True)
    raise SystemExit(1)


def detect_operation_type(
    source_wt: Path, target_wt: Path, ctx: WorkstackContext, repo_root: Path
) -> str:
    """Determine whether to move, swap, or create based on target existence.

    Returns "move", "swap", or "create".
    """
    target_exists = target_wt.exists()

    if not target_exists:
        return "create"

    # Target exists - check if it has a branch
    target_branch = _get_worktree_branch(ctx, repo_root, target_wt)
    if target_branch:
        return "swap"
    else:
        return "move"


def execute_move(
    ctx: WorkstackContext,
    repo_root: Path,
    source_wt: Path,
    target_wt: Path,
    fallback_ref: str,
    *,
    force: bool,
) -> None:
    """Execute move operation (target doesn't exist or is in detached HEAD).

    Moves the branch from source to target, then switches source to fallback_ref.
    """
    # Validate source has a branch
    source_branch = _get_worktree_branch(ctx, repo_root, source_wt)
    if source_branch is None:
        click.echo("Error: Source worktree is in detached HEAD state", err=True)
        raise SystemExit(1)

    # Check for uncommitted changes in source
    if ctx.git_ops.has_uncommitted_changes(source_wt) and not force:
        click.echo(
            f"Error: Uncommitted changes in source worktree '{source_wt.name}'.\n"
            f"Commit, stash, or use --force to override.",
            err=True,
        )
        raise SystemExit(1)

    target_exists = target_wt.exists()

    # To move branch from source to target, we need to avoid having the same branch
    # checked out in two places simultaneously. Strategy:
    # 1. Detach HEAD in source worktree (frees up source_branch)
    # 2. Create/checkout source_branch in target worktree
    # 3. Checkout fallback_ref in source worktree
    click.echo(f"Moving '{source_branch}' from '{source_wt.name}' to '{target_wt.name}'")
    ctx.git_ops.checkout_detached(source_wt, source_branch)

    if target_exists:
        # Target exists - check for uncommitted changes
        if ctx.git_ops.has_uncommitted_changes(target_wt) and not force:
            click.echo(
                f"Error: Uncommitted changes in target worktree '{target_wt.name}'.\n"
                f"Commit, stash, or use --force to override.",
                err=True,
            )
            raise SystemExit(1)

        # Checkout branch in existing target
        ctx.git_ops.checkout_branch(target_wt, source_branch)
    else:
        # Create new worktree with branch
        ctx.git_ops.add_worktree(
            repo_root, target_wt, branch=source_branch, ref=None, create_branch=False
        )

    # Check if fallback_ref is already checked out elsewhere, and detach it if needed
    fallback_wt = ctx.git_ops.is_branch_checked_out(repo_root, fallback_ref)
    if fallback_wt is not None and fallback_wt.resolve() != source_wt.resolve():
        # Fallback branch is checked out in another worktree, detach it first
        ctx.git_ops.checkout_detached(fallback_wt, fallback_ref)

    # Switch source to fallback branch
    ctx.git_ops.checkout_branch(source_wt, fallback_ref)

    click.echo(f"✓ Moved '{source_branch}' from '{source_wt.name}' to '{target_wt.name}'")


def execute_swap(
    ctx: WorkstackContext,
    repo_root: Path,
    source_wt: Path,
    target_wt: Path,
    *,
    force: bool,
) -> None:
    """Execute swap operation (both worktrees exist with branches).

    Swaps the branches between source and target worktrees.
    """
    source_branch = _get_worktree_branch(ctx, repo_root, source_wt)
    target_branch = _get_worktree_branch(ctx, repo_root, target_wt)

    if source_branch is None or target_branch is None:
        click.echo("Error: Both worktrees must have branches checked out for swap", err=True)
        raise SystemExit(1)

    # Check for uncommitted changes
    if ctx.git_ops.has_uncommitted_changes(source_wt) or ctx.git_ops.has_uncommitted_changes(
        target_wt
    ):
        if not force:
            click.echo(
                "Error: Uncommitted changes detected in one or more worktrees.\n"
                "Commit, stash, or use --force to override.",
                err=True,
            )
            raise SystemExit(1)

    # Confirm swap unless --force
    if not force:
        click.echo("This will swap branches between worktrees:")
        click.echo(f"  '{source_wt.name}': '{source_branch}' → '{target_branch}'")
        click.echo(f"  '{target_wt.name}': '{target_branch}' → '{source_branch}'")
        if not click.confirm("Continue?"):
            click.echo("Swap cancelled")
            raise SystemExit(0)

    click.echo(f"Swapping branches between '{source_wt.name}' and '{target_wt.name}'")

    # To swap branches between worktrees, we need to avoid having the same branch
    # checked out in two places simultaneously. Strategy:
    # 1. Detach HEAD in source worktree (frees up source_branch)
    # 2. Checkout source_branch in target worktree
    # 3. Checkout target_branch in source worktree
    ctx.git_ops.checkout_detached(source_wt, source_branch)
    ctx.git_ops.checkout_branch(target_wt, source_branch)
    ctx.git_ops.checkout_branch(source_wt, target_branch)

    click.echo(f"✓ Swapped '{source_branch}' ↔ '{target_branch}'")


@click.command("move")
@click.option("--current", is_flag=True, help="Use current worktree as source")
@click.option("--branch", help="Auto-detect worktree containing this branch")
@click.option("--worktree", help="Use specific worktree as source")
@click.option("--ref", default="main", help="Fallback branch for source after move (default: main)")
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompts")
@click.argument("target", required=True, shell_complete=complete_worktree_names)
@click.pass_obj
def move_cmd(
    ctx: WorkstackContext,
    current: bool,
    branch: str | None,
    worktree: str | None,
    ref: str,
    force: bool,
    target: str,
) -> None:
    """Move branches between worktrees with explicit source specification.

    Examples:

        \b
        # Move current branch back to repository root
        workstack move root

        \b
        # Move from current worktree to new worktree
        workstack move target-wt

        \b
        # Move from current worktree (explicit)
        workstack move --current target-wt

        \b
        # Auto-detect source from branch name
        workstack move --branch feature-x new-wt

        \b
        # Move from specific source to target
        workstack move --worktree old-wt new-wt

        \b
        # Swap branches between current and another worktree
        workstack move --current existing-wt

        \b
        # Force operation without prompts (for scripts)
        workstack move --current target-wt --force

        \b
        # Specify custom fallback branch
        workstack move --current new-wt --ref develop
    """
    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)
    workstacks_dir = ensure_workstacks_dir(repo)
    trunk_branch = ctx.repo_config_ops.get_trunk_branch(repo.root)

    # Resolve source worktree
    source_wt = resolve_source_worktree(
        ctx,
        repo.root,
        current=current,
        branch=branch,
        worktree=worktree,
        workstacks_dir=workstacks_dir,
    )

    # Resolve target worktree path
    # Special case: "root" refers to the repository root
    if target == "root":
        target_wt = repo.root
    else:
        target_wt = worktree_path_for(workstacks_dir, target)

    # Validate source and target are different
    if source_wt.resolve() == target_wt.resolve():
        click.echo("Error: Source and target worktrees are the same", err=True)
        raise SystemExit(1)

    # Detect operation type
    operation_type = detect_operation_type(source_wt, target_wt, ctx, repo.root)

    # Execute operation
    if operation_type == "swap":
        execute_swap(ctx, repo.root, source_wt, target_wt, force=force)
    else:
        # Auto-detect default branch if using 'main' default and it doesn't exist
        if ref == "main":
            detected_default = ctx.git_ops.detect_default_branch(repo.root, trunk_branch)
            ref = detected_default

        execute_move(ctx, repo.root, source_wt, target_wt, ref, force=force)
