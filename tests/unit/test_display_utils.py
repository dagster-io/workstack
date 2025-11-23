"""Tests for display formatting utilities."""

import click

from erk.core.display_utils import format_worktree_line


def test_format_worktree_line_with_pr_title() -> None:
    """Test format_worktree_line displays PR title without emoji prefix."""
    result = format_worktree_line(
        name="feature",
        branch="feature-branch",
        pr_info="✅ #123",
        plan_summary=None,
        is_root=False,
        is_current=False,
        pr_title="Add new feature",
    )

    # Remove styling to check content
    unstyled = click.unstyle(result)

    # Verify PR title is displayed
    assert "Add new feature" in unstyled

    # Verify PR title does NOT have emoji prefix
    assert "📋 Add new feature" not in unstyled
    assert "📋" not in unstyled


def test_format_worktree_line_pr_title_precedence() -> None:
    """Test that PR title takes precedence over plan summary."""
    result = format_worktree_line(
        name="feature",
        branch="feature-branch",
        pr_info="✅ #123",
        plan_summary="Plan summary text",
        is_root=False,
        is_current=False,
        pr_title="PR title from GitHub",
    )

    unstyled = click.unstyle(result)

    # Verify PR title is displayed
    assert "PR title from GitHub" in unstyled

    # Verify plan summary is NOT displayed
    assert "Plan summary text" not in unstyled

    # Verify emoji is not added to PR title
    assert "📋" not in unstyled


def test_format_worktree_line_plan_summary_fallback() -> None:
    """Test that plan summary is displayed with emoji when no PR title."""
    result = format_worktree_line(
        name="feature",
        branch="feature-branch",
        pr_info="✅ #123",
        plan_summary="Plan summary text",
        is_root=False,
        is_current=False,
        pr_title=None,  # No PR title
    )

    unstyled = click.unstyle(result)

    # Verify plan summary is displayed with emoji
    assert "📋 Plan summary text" in unstyled

    # Verify plan summary IS shown (not PR title placeholder)
    assert "Plan summary text" in unstyled


def test_format_worktree_line_no_plan_placeholder() -> None:
    """Test that [no plan] placeholder is displayed when no PR title or plan."""
    result = format_worktree_line(
        name="feature",
        branch="feature-branch",
        pr_info="✅ #123",
        plan_summary=None,  # No plan summary
        is_root=False,
        is_current=False,
        pr_title=None,  # No PR title
    )

    unstyled = click.unstyle(result)

    # Verify [no plan] placeholder is displayed
    assert "[no plan]" in unstyled

    # Verify no emoji is present
    assert "📋" not in unstyled
