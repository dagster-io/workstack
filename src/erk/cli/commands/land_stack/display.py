"""High-level display functions for land-stack command."""

import logging
import os

import click

from erk.cli.commands.land_stack.models import BranchPR
from erk.cli.commands.land_stack.output import _emit

logger = logging.getLogger(__name__)

# Enable debug logging if ERK_DEBUG environment variable is set
if os.getenv("ERK_DEBUG"):
    logging.basicConfig(level=logging.DEBUG, format="[DEBUG %(name)s:%(lineno)d] %(message)s")


def _show_landing_plan(
    current_branch: str,
    trunk_branch: str,
    branches: list[BranchPR],
    *,
    force: bool,
    dry_run: bool,
    script_mode: bool,
) -> None:
    """Display landing plan and get user confirmation.

    Args:
        current_branch: Name of current branch
        trunk_branch: Name of trunk branch (displayed at bottom)
        branches: List of BranchPR to land (bottom to top order)
        force: If True, skip confirmation
        dry_run: If True, skip confirmation and add dry-run prefix
        script_mode: True when running in --script mode (output to stderr)

    Raises:
        SystemExit: If user declines confirmation
    """
    logger.debug(
        "_show_landing_plan() called: branches=%s, force=%s", [b.branch for b in branches], force
    )

    # Display header
    header = "📋 Summary"
    if dry_run:
        header += click.style(" (dry run)", fg="bright_black")
    _emit(click.style(f"\n{header}", bold=True), script_mode=script_mode)
    _emit("", script_mode=script_mode)

    # Display summary
    pr_text = "PR" if len(branches) == 1 else "PRs"
    _emit(f"Landing {len(branches)} {pr_text}:", script_mode=script_mode)

    # Display PRs in format: #PR (branch → target) - title
    # Show in landing order (bottom to top)
    for branch_pr in branches:
        pr_styled = click.style(f"#{branch_pr.pr_number}", fg="cyan")
        branch_styled = click.style(branch_pr.branch, fg="yellow")
        trunk_styled = click.style(trunk_branch, fg="yellow")
        title_styled = click.style(branch_pr.title, fg="bright_magenta")

        line = f"  {pr_styled} ({branch_styled} → {trunk_styled}) - {title_styled}"
        _emit(line, script_mode=script_mode)

    _emit("", script_mode=script_mode)

    # Confirmation or force flag
    if dry_run:
        # No additional message needed - already indicated in header
        pass
    elif force:
        _emit("[--force flag set, proceeding without confirmation]", script_mode=script_mode)
    else:
        if not click.confirm("Proceed with landing these PRs?", default=False, err=script_mode):
            _emit("Landing cancelled.", script_mode=script_mode)
            raise SystemExit(0)


def _show_final_state(
    merged_branches: list[str],
    final_branch: str,
    *,
    dry_run: bool,
    script_mode: bool,
) -> None:
    """Display final state after landing operations.

    Args:
        merged_branches: List of successfully merged branch names
        final_branch: Name of current branch after all operations
        dry_run: If True, this was a dry run
        script_mode: True when running in --script mode (output to stderr)
    """
    _emit("Final state:", script_mode=script_mode)
    _emit("", script_mode=script_mode)

    # Success message
    pr_text = "PR" if len(merged_branches) == 1 else "PRs"
    success_msg = f"✅ Successfully landed {len(merged_branches)} {pr_text}"
    if dry_run:
        success_msg += click.style(" (dry run)", fg="bright_black")
    _emit(f"  {success_msg}", script_mode=script_mode)

    # Current branch
    branch_styled = click.style(final_branch, fg="yellow")
    _emit(f"  Current branch: {branch_styled}", script_mode=script_mode)

    # Merged branches
    branches_list = ", ".join(click.style(b, fg="yellow") for b in merged_branches)
    _emit(f"  Merged branches: {branches_list}", script_mode=script_mode)

    # Next steps
    _emit("", script_mode=script_mode)
    _emit(click.style("Next steps:", bold=True), script_mode=script_mode)
    _emit("  • Run 'erk sync -f' to remove worktrees for merged branches", script_mode=script_mode)
    _emit("  • Run 'gt sync -f' to rebase remaining stack branches (if needed)", script_mode=script_mode)
    _emit("", script_mode=script_mode)
    note_prefix = click.style("Note:", fg="yellow")
    _emit(f"{note_prefix} These commands are now manual to give you full control", script_mode=script_mode)
