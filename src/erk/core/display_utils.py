"""Display formatting utilities for erk.

This module contains pure business logic for formatting and displaying worktree
information in the CLI. All functions are pure (no I/O) and can be tested without
filesystem access.
"""

import re

import click

from erk.core.github.types import PullRequestInfo


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


def get_pr_status_emoji(pr: PullRequestInfo) -> str:
    """Determine the emoji to display for a PR based on its status.

    Args:
        pr: Pull request information

    Returns:
        Emoji character representing the PR's current state,
        with 💥 appended if there are merge conflicts
    """
    # Determine base emoji based on PR state
    if pr.is_draft:
        emoji = "🚧"
    elif pr.state == "MERGED":
        emoji = "🎉"
    elif pr.state == "CLOSED":
        emoji = "⛔"
    elif pr.checks_passing is True:
        emoji = "✅"
    elif pr.checks_passing is False:
        emoji = "❌"
    else:
        # Open PR with no checks
        emoji = "👀"

    # Append conflict indicator if PR has merge conflicts
    # Only for open PRs (published or draft)
    if pr.has_conflicts and pr.state == "OPEN":
        emoji += "💥"

    return emoji


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


def format_branch_without_worktree(
    branch_name: str,
    pr_info: str | None,
    max_branch_len: int = 0,
    max_pr_info_len: int = 0,
) -> str:
    """Format a branch without a worktree for display.

    Returns a line like: "branch-name PR #123 ✅"

    Args:
        branch_name: Name of the branch
        pr_info: Formatted PR info string (e.g., "✅ #23") or None
        max_branch_len: Maximum branch name length for alignment (0 disables)
        max_pr_info_len: Maximum PR info length for alignment (0 disables)

    Returns:
        Formatted string with branch name and PR info
    """
    # Format branch name in yellow (same as worktree branches)
    branch_styled = click.style(branch_name, fg="yellow")

    # Add padding to branch name if alignment is enabled
    if max_branch_len > 0:
        branch_padding = max_branch_len - len(branch_name)
        branch_styled += " " * branch_padding

    line = branch_styled

    # Add PR info if available
    if pr_info:
        # Calculate visible length for alignment
        pr_info_visible_len = get_visible_length(pr_info)

        # Add padding to PR info if alignment is enabled
        if max_pr_info_len > 0:
            pr_info_padding = max_pr_info_len - pr_info_visible_len
            pr_info_padded = pr_info + (" " * pr_info_padding)
        else:
            pr_info_padded = pr_info

        line += f" {pr_info_padded}"

    return line


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
    pr_title: str | None = None,
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
        pr_title: PR title from GitHub (preferred over plan_summary if available)

    Returns:
        Formatted line: name (branch) {PR info} {PR title or plan summary}
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

    # Add PR title, plan summary, or placeholder (PR title takes precedence)
    if pr_title:
        # PR title available - use it without emoji
        title_colored = click.style(pr_title, fg="bright_magenta")
        parts.append(title_colored)
    elif plan_summary:
        # No PR title but have plan summary - use with emoji
        plan_colored = click.style(f"📋 {plan_summary}", fg="bright_magenta")
        parts.append(plan_colored)
    else:
        # No PR title and no plan summary
        parts.append(click.style("[no plan]", fg="white", dim=True))

    # Build the main line
    line = " ".join(parts)

    # Add indicator on the right for current worktree
    if is_current:
        indicator = click.style(" ← (cwd)", fg="bright_blue")
        line += indicator

    return line


def format_plan_issue_display(
    plan_issue_identifier: str,
    state: str,
    title: str,
    labels: list[str],
    url: str | None = None,
) -> str:
    """Format a plan issue for display in lists.

    Args:
        plan_issue_identifier: Issue identifier (e.g., "42", "PROJ-123")
        state: Issue state ("OPEN" or "CLOSED")
        title: Issue title
        labels: List of label names
        url: Optional URL for clickable link

    Returns:
        Formatted string: "#42 (OPEN) [erk-plan] Title"
    """
    # Format state with color
    state_color = "green" if state == "OPEN" else "red"
    state_str = click.style(state, fg=state_color)

    # Format identifier
    id_text = f"#{plan_issue_identifier}"

    # If we have a URL, make it clickable using OSC 8
    if url:
        colored_id = click.style(id_text, fg="cyan")
        clickable_id = f"\033]8;;{url}\033\\{colored_id}\033]8;;\033\\"
    else:
        clickable_id = click.style(id_text, fg="cyan")

    # Format labels
    labels_str = ""
    if labels:
        labels_str = " " + " ".join(
            click.style(f"[{label}]", fg="bright_magenta") for label in labels
        )

    return f"{clickable_id} ({state_str}){labels_str} {title}"
