"""Unit tests for display_utils.py color formatting."""

from erk_shared.github.types import WorkflowRun

from erk.core.display_utils import format_workflow_run_id, format_worktree_line


def test_pr_title_uses_cyan() -> None:
    """Test that PR titles render with cyan color."""
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

    # Assert: Check for cyan ANSI escape code (36m)
    # ANSI cyan is \x1b[36m
    assert "\x1b[36m" in result, "Expected cyan color code for PR title"
    assert pr_title in result, "Expected PR title in output"


def test_plan_title_uses_bright_magenta() -> None:
    """Test that plan titles render with bright_magenta color."""
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

    # Assert: Check for bright magenta ANSI escape code (95m)
    # ANSI bright_magenta is \x1b[95m
    assert "\x1b[95m" in result, "Expected bright_magenta color code for plan title"
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

    # Assert: Should have cyan (PR title color), not bright_magenta (plan color)
    assert "\x1b[36m" in result, "Expected cyan for PR title"
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


def test_format_workflow_run_id_with_url() -> None:
    """Test that workflow run ID with URL is linkified and colored cyan."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="12345678",
        status="completed",
        conclusion="success",
        branch="main",
        head_sha="abc123",
    )
    workflow_url = "https://github.com/owner/repo/actions/runs/12345678"

    # Act
    result = format_workflow_run_id(workflow_run, workflow_url)

    # Assert: Check for cyan color and OSC 8 link
    assert "\x1b[36m" in result, "Expected cyan color code for run ID"
    assert "12345678" in result, "Expected run ID in output"
    assert "\x1b]8;;" in result, "Expected OSC 8 link escape sequence"
    assert workflow_url in result, "Expected workflow URL in link"


def test_format_workflow_run_id_without_url() -> None:
    """Test that workflow run ID without URL is colored but not linkified."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="87654321",
        status="in_progress",
        conclusion=None,
        branch="feature",
        head_sha="def456",
    )
    workflow_url = None

    # Act
    result = format_workflow_run_id(workflow_run, workflow_url)

    # Assert: Check for cyan color but no OSC 8 link
    assert "\x1b[36m" in result, "Expected cyan color code for run ID"
    assert "87654321" in result, "Expected run ID in output"
    assert "\x1b]8;;" not in result, "Should not have OSC 8 link without URL"


def test_format_workflow_run_id_none() -> None:
    """Test that None workflow run returns empty string."""
    # Act
    result = format_workflow_run_id(None, None)

    # Assert
    assert result == "", "Expected empty string for None workflow run"


def test_get_workflow_status_emoji_completed_success() -> None:
    """Test emoji for completed workflow with success conclusion."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="123",
        status="completed",
        conclusion="success",
        branch="main",
        head_sha="abc",
    )

    # Act
    from erk.core.display_utils import get_workflow_status_emoji

    result = get_workflow_status_emoji(workflow_run)

    # Assert
    assert result == "✅", "Expected green check for successful completion"


def test_get_workflow_status_emoji_completed_failure() -> None:
    """Test emoji for completed workflow with failure conclusion."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="456",
        status="completed",
        conclusion="failure",
        branch="main",
        head_sha="def",
    )

    # Act
    from erk.core.display_utils import get_workflow_status_emoji

    result = get_workflow_status_emoji(workflow_run)

    # Assert
    assert result == "❌", "Expected red X for failed completion"


def test_get_workflow_status_emoji_completed_cancelled() -> None:
    """Test emoji for completed workflow with cancelled conclusion."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="789",
        status="completed",
        conclusion="cancelled",
        branch="main",
        head_sha="ghi",
    )

    # Act
    from erk.core.display_utils import get_workflow_status_emoji

    result = get_workflow_status_emoji(workflow_run)

    # Assert
    assert result == "⛔", "Expected stop sign for cancelled workflow"


def test_get_workflow_status_emoji_in_progress() -> None:
    """Test emoji for in-progress workflow."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="101",
        status="in_progress",
        conclusion=None,
        branch="main",
        head_sha="jkl",
    )

    # Act
    from erk.core.display_utils import get_workflow_status_emoji

    result = get_workflow_status_emoji(workflow_run)

    # Assert
    assert result == "⟳", "Expected reload symbol for in-progress workflow"


def test_get_workflow_status_emoji_queued() -> None:
    """Test emoji for queued workflow."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="202",
        status="queued",
        conclusion=None,
        branch="main",
        head_sha="mno",
    )

    # Act
    from erk.core.display_utils import get_workflow_status_emoji

    result = get_workflow_status_emoji(workflow_run)

    # Assert
    assert result == "⧗", "Expected hourglass for queued workflow"


def test_get_workflow_status_emoji_unknown_status() -> None:
    """Test emoji for unknown workflow status."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="303",
        status="unknown_status",
        conclusion=None,
        branch="main",
        head_sha="pqr",
    )

    # Act
    from erk.core.display_utils import get_workflow_status_emoji

    result = get_workflow_status_emoji(workflow_run)

    # Assert
    assert result == "❓", "Expected question mark for unknown status"


def test_format_workflow_status_with_url() -> None:
    """Test format_workflow_status with URL includes OSC 8 linkification."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="555",
        status="completed",
        conclusion="success",
        branch="main",
        head_sha="stu",
    )
    workflow_url = "https://github.com/owner/repo/actions/runs/555"

    # Act
    from erk.core.display_utils import format_workflow_status

    result = format_workflow_status(workflow_run, workflow_url)

    # Assert
    assert "✅" in result, "Expected success emoji"
    assert "CI" in result, "Expected CI text"
    assert "\x1b[36m" in result, "Expected cyan color"
    assert "\x1b]8;;" in result, "Expected OSC 8 link escape sequence"
    assert workflow_url in result, "Expected URL in OSC 8 link"


def test_format_workflow_status_without_url() -> None:
    """Test format_workflow_status without URL displays plain colored text."""
    # Arrange
    workflow_run = WorkflowRun(
        run_id="666",
        status="in_progress",
        conclusion=None,
        branch="main",
        head_sha="vwx",
    )
    workflow_url = None

    # Act
    from erk.core.display_utils import format_workflow_status

    result = format_workflow_status(workflow_run, workflow_url)

    # Assert
    assert "⟳" in result, "Expected in-progress emoji"
    assert "CI" in result, "Expected CI text"
    assert "\x1b[36m" in result, "Expected cyan color"
    assert "\x1b]8;;" not in result, "Should not have OSC 8 link without URL"


def test_format_workflow_status_none_workflow() -> None:
    """Test format_workflow_status with None workflow returns empty string."""
    # Act
    from erk.core.display_utils import format_workflow_status

    result = format_workflow_status(None, None)

    # Assert
    assert result == "", "Expected empty string for None workflow"
