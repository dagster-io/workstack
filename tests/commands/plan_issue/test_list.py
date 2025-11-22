"""Tests for plan-issue list command."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.plan_issue import plan_issue_group
from erk.core.plan_issue_store import FakePlanIssueStore, PlanIssue, PlanIssueState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def test_list_plan_issues_no_filters() -> None:
    """Test listing all plan issues with no filters."""
    # Arrange
    issue1 = PlanIssue(
        plan_issue_identifier="1",
        title="Issue 1",
        body="",
        state=PlanIssueState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    issue2 = PlanIssue(
        plan_issue_identifier="2",
        title="Issue 2",
        body="",
        state=PlanIssueState.CLOSED,
        url="https://github.com/owner/repo/issues/2",
        labels=["bug"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanIssueStore(plan_issues={"1": issue1, "2": issue2})
        ctx = build_workspace_test_context(env, plan_issue_store=store)

        # Act
        result = runner.invoke(plan_issue_group, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 2 plan issue(s)" in result.output
        assert "#1" in result.output
        assert "Issue 1" in result.output
        assert "#2" in result.output
        assert "Issue 2" in result.output


def test_list_plan_issues_filter_by_state() -> None:
    """Test filtering plan issues by state."""
    # Arrange
    open_issue = PlanIssue(
        plan_issue_identifier="1",
        title="Open Issue",
        body="",
        state=PlanIssueState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    closed_issue = PlanIssue(
        plan_issue_identifier="2",
        title="Closed Issue",
        body="",
        state=PlanIssueState.CLOSED,
        url="https://github.com/owner/repo/issues/2",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanIssueStore(plan_issues={"1": open_issue, "2": closed_issue})
        ctx = build_workspace_test_context(env, plan_issue_store=store)

        # Act - Filter for open issues
        result = runner.invoke(plan_issue_group, ["list", "--state", "open"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 1 plan issue(s)" in result.output
        assert "#1" in result.output
        assert "Open Issue" in result.output
        assert "#2" not in result.output


def test_list_plan_issues_filter_by_labels() -> None:
    """Test filtering plan issues by labels with AND logic."""
    # Arrange
    issue_with_both = PlanIssue(
        plan_issue_identifier="1",
        title="Issue with both labels",
        body="",
        state=PlanIssueState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    issue_with_one = PlanIssue(
        plan_issue_identifier="2",
        title="Issue with one label",
        body="",
        state=PlanIssueState.OPEN,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanIssueStore(plan_issues={"1": issue_with_both, "2": issue_with_one})
        ctx = build_workspace_test_context(env, plan_issue_store=store)

        # Act - Filter for both labels (AND logic)
        result = runner.invoke(
            plan_issue_group,
            ["list", "--label", "erk-plan", "--label", "erk-queue"],
            obj=ctx,
        )

        # Assert
        assert result.exit_code == 0
        assert "Found 1 plan issue(s)" in result.output
        assert "#1" in result.output
        assert "Issue with both labels" in result.output
        assert "#2" not in result.output


def test_list_plan_issues_with_limit() -> None:
    """Test limiting the number of returned plan issues."""
    # Arrange
    issues = {}
    for i in range(1, 6):
        issues[str(i)] = PlanIssue(
            plan_issue_identifier=str(i),
            title=f"Issue {i}",
            body="",
            state=PlanIssueState.OPEN,
            url=f"https://github.com/owner/repo/issues/{i}",
            labels=[],
            assignees=[],
            created_at=datetime(2024, 1, i, tzinfo=UTC),
            updated_at=datetime(2024, 1, i, tzinfo=UTC),
            metadata={},
        )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanIssueStore(plan_issues=issues)
        ctx = build_workspace_test_context(env, plan_issue_store=store)

        # Act
        result = runner.invoke(plan_issue_group, ["list", "--limit", "2"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 2 plan issue(s)" in result.output


def test_list_plan_issues_combined_filters() -> None:
    """Test combining multiple filters."""
    # Arrange
    matching_issue = PlanIssue(
        plan_issue_identifier="1",
        title="Matching Issue",
        body="",
        state=PlanIssueState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan", "bug"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    wrong_state = PlanIssue(
        plan_issue_identifier="2",
        title="Wrong State",
        body="",
        state=PlanIssueState.CLOSED,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-plan", "bug"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )
    wrong_labels = PlanIssue(
        plan_issue_identifier="3",
        title="Wrong Labels",
        body="",
        state=PlanIssueState.OPEN,
        url="https://github.com/owner/repo/issues/3",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 3, tzinfo=UTC),
        updated_at=datetime(2024, 1, 3, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanIssueStore(
            plan_issues={"1": matching_issue, "2": wrong_state, "3": wrong_labels}
        )
        ctx = build_workspace_test_context(env, plan_issue_store=store)

        # Act
        result = runner.invoke(
            plan_issue_group,
            [
                "list",
                "--state",
                "open",
                "--label",
                "erk-plan",
                "--label",
                "bug",
            ],
            obj=ctx,
        )

        # Assert
        assert result.exit_code == 0
        assert "Found 1 plan issue(s)" in result.output
        assert "#1" in result.output
        assert "Matching Issue" in result.output


def test_list_plan_issues_empty_results() -> None:
    """Test querying with filters that match no issues."""
    # Arrange
    issue = PlanIssue(
        plan_issue_identifier="1",
        title="Issue",
        body="",
        state=PlanIssueState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanIssueStore(plan_issues={"1": issue})
        ctx = build_workspace_test_context(env, plan_issue_store=store)

        # Act
        result = runner.invoke(plan_issue_group, ["list", "--state", "closed"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "No plan issues found matching the criteria" in result.output
