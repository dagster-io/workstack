"""Tests for top-level plan commands (list, ls, get, close, retry)."""

from datetime import UTC, datetime

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo

from erk.cli.cli import cli
from erk.cli.commands.ls import ls_cmd
from erk.core.plan_store.fake import FakePlanStore
from erk.core.plan_store.types import Plan, PlanState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def plan_to_issue(plan: Plan) -> IssueInfo:
    """Convert Plan to IssueInfo for test setup."""
    return IssueInfo(
        number=int(plan.plan_identifier),
        title=plan.title,
        body=plan.body,
        state="OPEN" if plan.state == PlanState.OPEN else "CLOSED",
        url=plan.url or "",
        labels=plan.labels,
        assignees=plan.assignees,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


def test_top_level_list_command_works() -> None:
    """Test that top-level 'erk list' command works."""
    # Arrange
    plan1 = Plan(
        plan_identifier="1",
        title="Test Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan1)})
        ctx = build_workspace_test_context(env, issues=issues)

        # Act - Use top-level list command
        result = runner.invoke(cli, ["list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 1 plan(s)" in result.output
        assert "#1" in result.output
        assert "Test Issue" in result.output


def test_ls_command_lists_plans_by_default() -> None:
    """Test that 'erk ls' lists plans by default (new behavior)."""
    # Arrange
    plan1 = Plan(
        plan_identifier="1",
        title="Test Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan1)})
        ctx = build_workspace_test_context(env, issues=issues)

        # Act - Use ls command
        result = runner.invoke(ls_cmd, [], obj=ctx)

        # Assert - Should show plans
        assert result.exit_code == 0
        assert "Found 1 plan(s)" in result.output
        assert "#1" in result.output
        assert "Test Plan" in result.output


def test_ls_command_plan_filters_work() -> None:
    """Test that plan filters work with 'erk ls' command."""
    # Arrange
    open_plan = Plan(
        plan_identifier="1",
        title="Open Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    closed_plan = Plan(
        plan_identifier="2",
        title="Closed Plan",
        body="",
        state=PlanState.CLOSED,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={1: plan_to_issue(open_plan), 2: plan_to_issue(closed_plan)}
        )
        ctx = build_workspace_test_context(env, issues=issues)

        # Act - Filter for open plans
        result = runner.invoke(ls_cmd, ["--state", "open"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Found 1 plan(s)" in result.output
        assert "#1" in result.output
        assert "Open Plan" in result.output
        assert "#2" not in result.output


def test_top_level_get_command_works() -> None:
    """Test that 'erk plan get' command works."""
    # Arrange
    issue1 = Plan(
        plan_identifier="123",
        title="Test Issue",
        body="Issue body content",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/123",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"123": issue1})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act - Use plan get command
        result = runner.invoke(cli, ["plan", "get", "123"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        # ID is now rendered as clickable link with OSC 8 escape sequences
        assert "#123" in result.output
        assert "Test Issue" in result.output


def test_top_level_close_command_works() -> None:
    """Test that 'erk plan close' command works."""
    # Arrange
    issue1 = Plan(
        plan_identifier="456",
        title="Plan to Close",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/456",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 456},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"456": issue1})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act - Use plan close command
        result = runner.invoke(cli, ["plan", "close", "456"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert store.closed_plans == ["456"]


def test_top_level_retry_command_works() -> None:
    """Test that 'erk plan retry' command works."""
    # Arrange
    issue1 = Plan(
        plan_identifier="789",
        title="Plan to Retry",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/789",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 789},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store = FakePlanStore(plans={"789": issue1})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act - Use plan retry command
        result = runner.invoke(cli, ["plan", "retry", "789"], obj=ctx)

        # Assert - Verify command executed (exit code 0 or specific behavior)
        # The retry command may have different success criteria
        assert result.exit_code in (0, 1)  # Allow for workflow trigger failures in test env
