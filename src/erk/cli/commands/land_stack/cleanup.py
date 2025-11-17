"""Cleanup and navigation operations for land-stack command."""

import subprocess
from pathlib import Path

import click

from erk.cli.commands.land_stack.output import _emit, _format_cli_command
from erk.core.context import ErkContext


def _cleanup_and_navigate(
    ctx: ErkContext,
    repo_root: Path,
    merged_branches: list[str],
    trunk_branch: str,
    *,
    verbose: bool,
    dry_run: bool,
    script_mode: bool,
) -> str:
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
        Name of branch after cleanup and navigation
    """
    check = click.style("✓", fg="green")

    # Print section header
    _emit("", script_mode=script_mode)
    _emit("Cleaning up...", script_mode=script_mode)

    # Get last merged branch to find next unmerged child
    last_merged = merged_branches[-1] if merged_branches else None

    # Step 1: Checkout trunk branch
    if not dry_run:
        ctx.git_ops.checkout_branch(repo_root, trunk_branch)
    _emit(_format_cli_command(f"git checkout {trunk_branch}", check), script_mode=script_mode)
    final_branch = trunk_branch

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
    # Check if last merged branch had unmerged children
    if last_merged:
        all_branches = ctx.graphite_ops.get_all_branches(ctx.git_ops, repo_root)
        if last_merged in all_branches:
            children = all_branches[last_merged].children or []
            # Check if any children still exist and are unmerged
            for child in children:
                if child in all_branches:
                    if not dry_run:
                        try:
                            ctx.git_ops.checkout_branch(repo_root, child)
                            cmd = _format_cli_command(f"git checkout {child}", check)
                            _emit(cmd, script_mode=script_mode)
                            final_branch = child
                            return final_branch
                        except Exception:
                            pass  # Child branch may have been deleted
                    else:
                        cmd = _format_cli_command(f"git checkout {child}", check)
                        _emit(cmd, script_mode=script_mode)
                        final_branch = child
                        return final_branch

    # No unmerged children, stay on trunk (already checked out above)
    return final_branch
