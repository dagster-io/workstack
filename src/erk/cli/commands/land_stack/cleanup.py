"""Cleanup and navigation operations for land-stack command."""

from pathlib import Path

import click

from erk.cli.commands.land_stack.output import _emit, _format_cli_command
from erk.core.branch_metadata import BranchMetadata
from erk.core.context import ErkContext, regenerate_context
from erk.core.git.abc import WorktreeInfo


def _find_next_unmerged_child(
    last_merged_branch: str,
    all_branches: dict[str, BranchMetadata],
) -> str | None:
    """Find the first unmerged child of the last merged branch.

    Args:
        last_merged_branch: Name of the last branch that was merged
        all_branches: Dictionary mapping branch names to their metadata

    Returns:
        Name of the first unmerged child branch, or None if no children exist
    """
    if last_merged_branch not in all_branches:
        return None

    children = all_branches[last_merged_branch].children or []
    for child in children:
        if child in all_branches:
            return child

    return None


def _find_worktree_for_branch(
    branch: str,
    worktrees: list[WorktreeInfo],
) -> WorktreeInfo | None:
    """Find the worktree containing the specified branch.

    Args:
        branch: Name of the branch to search for
        worktrees: List of worktree information

    Returns:
        WorktreeInfo for the branch, or None if not found
    """
    for wt in worktrees:
        if wt.branch == branch:
            return wt
    return None


def _navigate_to_child_worktree(
    ctx: ErkContext,
    child_branch: str,
    child_worktree: WorktreeInfo,
    *,
    dry_run: bool,
    script_mode: bool,
) -> tuple[ErkContext, str, Path] | None:
    """Navigate to the child worktree and return updated context.

    Args:
        ctx: Current ErkContext
        child_branch: Name of the child branch
        child_worktree: WorktreeInfo for the child branch
        dry_run: If True, don't actually change directory
        script_mode: True when running in --script mode

    Returns:
        Tuple of (updated_context, branch_name, worktree_path), or None if navigation fails
    """
    check = click.style("✓", fg="green")

    if not dry_run and not script_mode:
        # In normal mode, check path exists before attempting to navigate
        if not child_worktree.path.exists():
            return None

        # Change process directory to child's worktree
        if not ctx.git.safe_chdir(child_worktree.path):
            return None

        ctx = regenerate_context(ctx)

    # In script mode, don't change directory - shell integration handles it
    cmd = _format_cli_command(f"git checkout {child_branch}", check)
    _emit(cmd, script_mode=script_mode)

    return (ctx, child_branch, child_worktree.path)


def _cleanup_and_navigate(
    ctx: ErkContext,
    repo_root: Path,
    merged_branches: list[str],
    trunk_branch: str,
    *,
    verbose: bool,
    dry_run: bool,
    script_mode: bool,
) -> tuple[str, Path]:
    """Clean up merged worktrees and navigate to appropriate branch.

    Args:
        ctx: ErkContext with access to operations
        repo_root: Repository root directory
        merged_branches: List of successfully merged branch names
        trunk_branch: Name of the trunk branch (e.g., "main" or "master")
        verbose: If True, show detailed output
        dry_run: If True, show what would be done without executing
        script_mode: True when running in --script mode (output to stderr)

    Returns:
        Tuple of (branch_name, worktree_path) after cleanup and navigation
    """
    check = click.style("✓", fg="green")

    # Print section header
    _emit("", script_mode=script_mode)
    _emit("Cleaning up...", script_mode=script_mode)

    # Get last merged branch to find next unmerged child
    last_merged = merged_branches[-1] if merged_branches else None

    # Step 1: Navigate to trunk worktree (repo root)
    # Only checkout if not already on trunk (avoids duplicate checkout message)
    current_branch = ctx.git.get_current_branch(repo_root)
    if current_branch != trunk_branch:
        if not dry_run and not script_mode:
            # In normal mode, change process directory to repo root
            if ctx.git.safe_chdir(repo_root):
                ctx = regenerate_context(ctx)
        # In script mode, don't change directory - shell integration handles it
        _emit(_format_cli_command(f"git checkout {trunk_branch}", check), script_mode=script_mode)
    final_branch = trunk_branch
    final_path = repo_root

    # Step 2: Inform user about manual cleanup
    _emit("  ℹ️  Run 'gt sync -f' to remove worktrees for merged branches", script_mode=script_mode)

    # Step 3: Navigate to next branch or stay on trunk
    # If last merged branch had unmerged children, navigate to one of them
    if not last_merged:
        return (final_branch, final_path)

    all_branches = ctx.graphite.get_all_branches(ctx.git, repo_root)
    child_branch = _find_next_unmerged_child(last_merged, all_branches)

    if not child_branch:
        return (final_branch, final_path)

    worktrees = ctx.git.list_worktrees(repo_root)
    child_worktree = _find_worktree_for_branch(child_branch, worktrees)

    if not child_worktree:
        # Child branch exists but no worktree found - stay on trunk
        return (final_branch, final_path)

    result = _navigate_to_child_worktree(
        ctx,
        child_branch,
        child_worktree,
        dry_run=dry_run,
        script_mode=script_mode,
    )

    if result is None:
        # Worktree path doesn't exist, stay on trunk
        return (final_branch, final_path)

    ctx, final_branch, final_path = result
    return (final_branch, final_path)
