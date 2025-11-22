"""Tests for plan-issue enqueue command."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.plan_issue import plan_issue_group
from erk.core.github.issues import FakeGitHubIssues, IssueInfo
from erk.core.plan_issue_store import FakePlanIssueStore, PlanIssue, PlanIssueState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def test_enqueue_plan_issue_adds_label() -> None:
    """Test enqueuing a plan issue adds erk-queue label."""
    # Arrange
    plan_issue = PlanIssue(
        plan_issue_identifier="42",
        title="Test Issue",
        body="Test body",
        state=PlanIssueState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"number": 42},
    )

    issue_info = IssueInfo(
        number=42,
        title="Test Issue",
        body="Test body",
        state="OPEN",
        url="https://github.com/owner/repo/issues/42",
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanIssueStore(plan_issues={"42": plan_issue})
        issues = FakeGitHubIssues(issues={42: issue_info})
        ctx = build_workspace_test_context(env, plan_issue_store=store, issues=issues)

        # Act
        result = runner.invoke(plan_issue_group, ["enqueue", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "✓" in result.output
        assert "erk-queue" in result.output
        assert "#42" in result.output
        assert "GitHub Actions" in result.output

        # Verify label was added
        assert issues.added_labels == [(42, ["erk-queue"])]

        # Verify erk-queue label was created in repo
        assert "erk-queue" in issues.labels
        assert any(
            label == "erk-queue" and color == "FFA500" for label, _, color in issues.created_labels
        )


def test_enqueue_plan_issue_not_found() -> None:
    """Test enqueuing a plan issue that doesn't exist."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanIssueStore(plan_issues={})
        issues = FakeGitHubIssues()
        ctx = build_workspace_test_context(env, plan_issue_store=store, issues=issues)

        # Act
        result = runner.invoke(plan_issue_group, ["enqueue", "999"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error" in result.output

        # Verify no label operations occurred
        assert issues.added_labels == []


def test_enqueue_plan_issue_label_already_exists() -> None:
    """Test enqueuing when erk-queue label already exists in repo."""
    # Arrange
    plan_issue = PlanIssue(
        plan_issue_identifier="123",
        title="Another Issue",
        body="Body",
        state=PlanIssueState.OPEN,
        url="https://github.com/owner/repo/issues/123",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 123},
    )

    issue_info = IssueInfo(
        number=123,
        title="Another Issue",
        body="Body",
        state="OPEN",
        url="https://github.com/owner/repo/issues/123",
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanIssueStore(plan_issues={"123": plan_issue})
        # Pre-configure erk-queue label as existing
        issues = FakeGitHubIssues(issues={123: issue_info}, labels={"erk-queue"})
        ctx = build_workspace_test_context(env, plan_issue_store=store, issues=issues)

        # Act
        result = runner.invoke(plan_issue_group, ["enqueue", "123"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "✓" in result.output

        # Verify label was added to issue
        assert issues.added_labels == [(123, ["erk-queue"])]

        # Verify no new label was created (already existed)
        assert issues.created_labels == []


def test_enqueue_plan_issue_shows_warning() -> None:
    """Test that enqueue shows warning about GitHub Actions automation."""
    # Arrange
    plan_issue = PlanIssue(
        plan_issue_identifier="50",
        title="Test",
        body="",
        state=PlanIssueState.OPEN,
        url="https://github.com/owner/repo/issues/50",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 50},
    )

    issue_info = IssueInfo(
        number=50,
        title="Test",
        body="",
        state="OPEN",
        url="https://github.com/owner/repo/issues/50",
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanIssueStore(plan_issues={"50": plan_issue})
        issues = FakeGitHubIssues(issues={50: issue_info})
        ctx = build_workspace_test_context(env, plan_issue_store=store, issues=issues)

        # Act
        result = runner.invoke(plan_issue_group, ["enqueue", "50"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Note:" in result.output or "⚠" in result.output
        assert "automatically" in result.output.lower()
        assert "Actions" in result.output
