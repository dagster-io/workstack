"""Unit tests for display_utils.py color formatting."""

from erk.core.display_utils import format_worktree_line


def test_pr_title_uses_bright_magenta() -> None:
    """Test that PR titles render with bright_magenta color."""
    # Arrange
    name = "feature-branch"
    branch = "feature-branch"
    pr_info = "#123"
    pr_title = "Add new feature"
    plan_summary = None

    # Act
    result = format_worktree_line(
        name=name,
        branch=branch,
        pr_info=pr_info,
        plan_summary=plan_summary,
        is_root=False,
        is_current=False,
        pr_title=pr_title,
    )

    # Assert: Check for bright magenta ANSI escape code (95m)
    # ANSI bright_magenta is \x1b[95m
    assert "\x1b[95m" in result, "Expected bright_magenta color code for PR title"
    assert pr_title in result, "Expected PR title in output"


def test_plan_title_uses_cyan() -> None:
    """Test that plan titles render with cyan color."""
    # Arrange
    name = "feature-branch"
    branch = "feature-branch"
    pr_info = None
    pr_title = None
    plan_summary = "Implementation Plan for Feature"

    # Act
    result = format_worktree_line(
        name=name,
        branch=branch,
        pr_info=pr_info,
        plan_summary=plan_summary,
        is_root=False,
        is_current=False,
        pr_title=pr_title,
    )

    # Assert: Check for cyan ANSI escape code (36m)
    # ANSI cyan is \x1b[36m
    assert "\x1b[36m" in result, "Expected cyan color code for plan title"
    assert plan_summary in result, "Expected plan summary in output"
    assert "📋" in result, "Expected plan emoji in output"


def test_pr_title_takes_precedence_over_plan() -> None:
    """Test color differentiation when both PR and plan exist (PR takes precedence)."""
    # Arrange
    name = "feature-branch"
    branch = "feature-branch"
    pr_info = "#123"
    pr_title = "Add new feature"
    plan_summary = "Implementation Plan for Feature"

    # Act
    result = format_worktree_line(
        name=name,
        branch=branch,
        pr_info=pr_info,
        plan_summary=plan_summary,
        is_root=False,
        is_current=False,
        pr_title=pr_title,
    )

    # Assert: Should have bright_magenta (PR title color), not cyan (plan color)
    assert "\x1b[95m" in result, "Expected bright_magenta for PR title"
    assert pr_title in result, "Expected PR title in output"
    # Plan summary should NOT appear when PR title exists
    assert plan_summary not in result, "Plan summary should not appear when PR title exists"
    # Should NOT have plan emoji when showing PR title
    assert "📋" not in result, "Plan emoji should not appear when PR title exists"


def test_no_plan_placeholder_uses_dimmed_white() -> None:
    """Test that [no plan] placeholder uses dimmed white color."""
    # Arrange
    name = "feature-branch"
    branch = "feature-branch"
    pr_info = None
    pr_title = None
    plan_summary = None

    # Act
    result = format_worktree_line(
        name=name,
        branch=branch,
        pr_info=pr_info,
        plan_summary=plan_summary,
        is_root=False,
        is_current=False,
        pr_title=pr_title,
    )

    # Assert: Check for white color (37m) and dim (2m)
    # The ANSI codes appear as separate sequences: \x1b[37m\x1b[2m
    assert "\x1b[" in result, "Expected ANSI escape codes"
    assert "[no plan]" in result, "Expected [no plan] placeholder"
    # Check for dim modifier (can be separate or combined)
    assert "\x1b[2m" in result or "2;" in result or ";2m" in result, "Expected dim modifier"
    assert "37m" in result, "Expected white color code"
