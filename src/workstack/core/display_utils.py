"""Display formatting utilities for workstack.

This module contains pure business logic for formatting and displaying worktree
information in the CLI. All functions are pure (no I/O) and can be tested without
filesystem access.
"""

import re

import click

from workstack.core.github_ops import PullRequestInfo


def get_visible_length(text: str) -> int:
    """Calculate the visible length of text, excluding ANSI and OSC escape sequences.

    Args:
        text: Text that may contain escape sequences

    Returns:
        Number of visible characters
    """
    # Remove ANSI color codes (\033[...m)
    text = re.sub(r"\033\[[0-9;]*m", "", text)
    # Remove OSC 8 hyperlink sequences (\033]8;;URL\033\\)
    text = re.sub(r"\033\]8;;[^\033]*\033\\", "", text)
    return len(text)


def filter_stack_for_worktree(
    stack: list[str],
    current_branch: str,
    all_checked_out_branches: set[str],
    is_root_worktree: bool,
) -> list[str]:
    """Filter a graphite stack to only show branches relevant to the current worktree.

    When displaying a stack for a specific worktree, we want to show:
    - Root worktree: Current branch + all ancestors (no descendants)
    - Other worktrees: Ancestors + current + descendants that are checked out somewhere

    This ensures that:
    - Root worktree shows context from trunk down to current branch
    - Other worktrees show full context but only "active" descendants with worktrees
    - Branches without active worktrees don't clutter non-root displays

    Example:
        Stack: [main, foo, bar, baz]
        Worktrees:
          - root on bar
          - worktree-baz on baz

        Root display: [main, foo, bar]  (ancestors + current, no descendants)
        Worktree-baz display: [main, foo, bar, baz]  (full context with checked-out descendants)

    Args:
        stack: The full graphite stack (ordered from trunk to leaf)
        current_branch: Branch checked out in the current worktree
        all_checked_out_branches: Set of all branches checked out in any worktree
        is_root_worktree: True if this is the root repository worktree

    Returns:
        Filtered stack with only relevant branches
    """
    if current_branch not in stack:
        # If current branch is not in stack (shouldn't happen), return full stack
        return stack

    # Find the index of the current branch in the stack
    current_idx = stack.index(current_branch)

    # Filter the stack based on whether this is the root worktree
    if is_root_worktree:
        # Root worktree: show only ancestors + current (no descendants)
        # This keeps the display clean and focused on context
        return stack[: current_idx + 1]
    else:
        # Non-root worktree: show ancestors + current + descendants with worktrees
        result = []
        for i, branch in enumerate(stack):
            if i <= current_idx:
                # Ancestors and current branch: always keep
                result.append(branch)
            else:
                # Descendants: only keep if checked out in some worktree
                if branch in all_checked_out_branches:
                    result.append(branch)

        return result


def get_pr_status_emoji(pr: PullRequestInfo) -> str:
    """Determine the emoji to display for a PR based on its status.

    Args:
        pr: Pull request information

    Returns:
        Emoji character representing the PR's current state
    """
    if pr.is_draft:
        return "🚧"
    if pr.state == "MERGED":
        return "🟣"
    if pr.state == "CLOSED":
        return "⭕"
    if pr.checks_passing is True:
        return "✅"
    if pr.checks_passing is False:
        return "❌"
    # Open PR with no checks
    return "◯"


def format_pr_info(
    pr: PullRequestInfo | None,
    graphite_url: str | None,
) -> str:
    """Format PR status indicator with emoji and link.

    Args:
        pr: Pull request information (None if no PR exists)
        graphite_url: Graphite URL for the PR (None if unavailable)

    Returns:
        Formatted PR info string (e.g., "✅ #23") or empty string if no PR
    """
    if pr is None:
        return ""

    emoji = get_pr_status_emoji(pr)

    # Format PR number text
    pr_text = f"#{pr.number}"

    # If we have a URL, make it clickable using OSC 8 terminal escape sequence
    if graphite_url:
        # Wrap the link text in cyan color to distinguish from non-clickable bright_blue indicators
        colored_pr_text = click.style(pr_text, fg="cyan")
        clickable_link = f"\033]8;;{graphite_url}\033\\{colored_pr_text}\033]8;;\033\\"
        return f"{emoji} {clickable_link}"
    else:
        # No URL available - just show colored text without link
        colored_pr_text = click.style(pr_text, fg="cyan")
        return f"{emoji} {colored_pr_text}"


def format_worktree_line(
    name: str,
    branch: str | None,
    pr_info: str | None,
    plan_summary: str | None,
    is_root: bool,
    is_current: bool,
    max_name_len: int = 0,
    max_branch_len: int = 0,
    max_pr_info_len: int = 0,
) -> str:
    """Format a single worktree line with colorization and optional alignment.

    Args:
        name: Worktree name to display
        branch: Branch name (if any)
        pr_info: Formatted PR info string (e.g., "✅ #23") or None
        plan_summary: Plan title or None if no plan
        is_root: True if this is the root repository worktree
        is_current: True if this is the worktree the user is currently in
        max_name_len: Maximum name length for alignment (0 = no alignment)
        max_branch_len: Maximum branch length for alignment (0 = no alignment)
        max_pr_info_len: Maximum PR info visible length for alignment (0 = no alignment)

    Returns:
        Formatted line with colorization in format: name (branch) {PR info} {plan summary}
    """
    # Root worktree gets green to distinguish it from regular worktrees
    name_color = "green" if is_root else "cyan"

    # Calculate padding for name field
    name_padding = max_name_len - len(name) if max_name_len > 0 else 0
    name_with_padding = name + (" " * name_padding)
    name_part = click.style(name_with_padding, fg=name_color, bold=True)

    # Build parts for display: name (branch) {PR info} {plan summary}
    parts = [name_part]

    # Add branch in parentheses (yellow)
    # If name matches branch, show "=" instead of repeating the branch name
    if branch:
        branch_display = "=" if name == branch else branch
        # Calculate padding for branch field (including parentheses)
        branch_with_parens = f"({branch_display})"
        branch_padding = max_branch_len - len(branch_with_parens) if max_branch_len > 0 else 0
        branch_with_padding = branch_with_parens + (" " * branch_padding)
        branch_part = click.style(branch_with_padding, fg="yellow")
        parts.append(branch_part)
    elif max_branch_len > 0:
        # Add spacing even if no branch to maintain alignment
        parts.append(" " * max_branch_len)

    # Add PR info or placeholder with alignment
    pr_info_placeholder = click.style("[no PR]", fg="white", dim=True)
    pr_display = pr_info if pr_info else pr_info_placeholder

    if max_pr_info_len > 0:
        # Calculate visible length and add padding
        visible_len = get_visible_length(pr_display)
        padding = max_pr_info_len - visible_len
        pr_display_with_padding = pr_display + (" " * padding)
        parts.append(pr_display_with_padding)
    else:
        parts.append(pr_display)

    # Add plan summary or placeholder
    if plan_summary:
        plan_colored = click.style(f"📋 {plan_summary}", fg="bright_magenta")
        parts.append(plan_colored)
    else:
        parts.append(click.style("[no plan]", fg="white", dim=True))

    # Build the main line
    line = " ".join(parts)

    # Add indicator on the right for current worktree
    if is_current:
        indicator = click.style(" ← (cwd)", fg="bright_blue")
        line += indicator

    return line
