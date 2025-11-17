"""Cleanup and navigation operations for land-stack command."""

import subprocess
from pathlib import Path

import click

from erk.cli.commands.land_stack.output import _emit, _format_cli_command
from erk.core.context import ErkContext, regenerate_context


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
    current_branch = ctx.git_ops.get_current_branch(repo_root)
    if current_branch != trunk_branch:
        if not dry_run and not script_mode:
            # In normal mode, change process directory to repo root
            if ctx.git_ops.safe_chdir(repo_root):
                ctx = regenerate_context(ctx)
        # In script mode, don't change directory - shell integration handles it
        _emit(_format_cli_command(f"git checkout {trunk_branch}", check), script_mode=script_mode)
    final_branch = trunk_branch
    final_path = repo_root

    # Step 2: Sync worktrees
    base_cmd = "erk sync -f"
    if verbose:
        base_cmd += " --verbose"

    if dry_run:
        _emit(_format_cli_command(base_cmd, check), script_mode=script_mode)
    else:
        try:
            # This will remove merged worktrees and delete branches
            ctx.shell_ops.run_erk_sync(
                repo_root,
                force=True,
                verbose=verbose,
            )
            _emit(_format_cli_command(base_cmd, check), script_mode=script_mode)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            _emit(
                f"Warning: Cleanup sync failed: {error_msg}",
                script_mode=script_mode,
                error=True,
            )

    # Step 3: Navigate to next branch or stay on trunk
    # If last merged branch had unmerged children, navigate to one of them
    if last_merged:
        all_branches = ctx.graphite_ops.get_all_branches(ctx.git_ops, repo_root)
        if last_merged in all_branches:
            children = all_branches[last_merged].children or []
            # Check if any children still exist and are unmerged
            for child in children:
                if child in all_branches:
                    # Find worktree containing child branch
                    worktrees = ctx.git_ops.list_worktrees(repo_root)
                    for wt in worktrees:
                        if wt.branch == child:
                            if not dry_run and not script_mode:
                                # In normal mode, change process directory to child's worktree
                                if ctx.git_ops.safe_chdir(wt.path):
                                    ctx = regenerate_context(ctx)
                                else:
                                    # Worktree path doesn't exist, continue to next child
                                    continue
                            # In script mode, don't change directory - shell integration handles it
                            cmd = _format_cli_command(f"git checkout {child}", check)
                            _emit(cmd, script_mode=script_mode)
                            final_branch = child
                            final_path = wt.path
                            return (final_branch, final_path)
                    # Child branch exists but no worktree found - stay on trunk
                    break

    # No unmerged children or no worktree found, return trunk
    return (final_branch, final_path)
