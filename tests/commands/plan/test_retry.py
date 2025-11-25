"""Tests for plan retry command."""

from datetime import UTC, datetime

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo
from erk_shared.github.metadata import create_metadata_block, render_erk_issue_event

from erk.cli.cli import cli
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def test_retry_success_first_time() -> None:
    """Test retrying a plan for the first time."""
    # Arrange: Create issue with erk-plan label
    issue = IssueInfo(
        number=42,
        title="Test Plan",
        body="Test plan body",
        state="OPEN",
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
    )

    github_issues = FakeGitHubIssues(
        issues={42: issue},
        comments={42: []},  # No previous retry comments
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=github_issues)

        # Act
        result = runner.invoke(cli, ["retry", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Fetched issue #42" in result.output
        assert "Parsing 0 comment(s) for retry history" in result.output
        assert "Triggering dispatch-erk-queue workflow..." in result.output
        assert "✓ Plan #42 requeued (retry #1)" in result.output
        assert "View issue: https://github.com/owner/repo/issues/42" in result.output

        # Verify workflow was triggered
        assert len(ctx.github.triggered_workflows) == 1
        workflow, inputs = ctx.github.triggered_workflows[0]
        assert workflow == "dispatch-erk-queue.yml"
        assert inputs["issue_number"] == "42"

        # Verify metadata comment was posted
        assert len(github_issues.added_comments) == 1
        comment_issue_num, comment_body = github_issues.added_comments[0]
        assert comment_issue_num == 42
        assert "plan-retry" in comment_body
        assert "retry #1" in comment_body


def test_retry_success_subsequent() -> None:
    """Test retrying a plan that was already retried once."""
    # Arrange: Create issue with previous retry comment
    issue = IssueInfo(
        number=42,
        title="Test Plan",
        body="Test plan body",
        state="OPEN",
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
    )

    # Create previous retry metadata comment
    previous_retry_timestamp = "2024-01-10T10:00:00+00:00"
    metadata_block = create_metadata_block(
        key="plan-retry",
        data={
            "retry_timestamp": previous_retry_timestamp,
            "triggered_by": "user1",
            "retry_count": 1,
        },
    )
    previous_retry_comment = render_erk_issue_event(
        title="🔄 Plan requeued (retry #1)",
        metadata=metadata_block,
    )

    github_issues = FakeGitHubIssues(
        issues={42: issue},
        comments={42: [previous_retry_comment]},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=github_issues)

        # Act
        result = runner.invoke(cli, ["retry", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Fetched issue #42" in result.output
        assert "Parsing 1 comment(s) for retry history" in result.output
        assert "Triggering dispatch-erk-queue workflow..." in result.output
        assert "✓ Plan #42 requeued (retry #2)" in result.output
        assert "View issue: https://github.com/owner/repo/issues/42" in result.output

        # Verify new comment has retry_count=2
        assert len(github_issues.added_comments) == 1
        comment_issue_num, comment_body = github_issues.added_comments[0]
        assert comment_issue_num == 42
        assert "plan-retry" in comment_body
        assert "retry #2" in comment_body


def test_retry_error_closed_issue() -> None:
    """Test retrying a closed plan fails with error."""
    # Arrange: Create closed issue
    issue = IssueInfo(
        number=42,
        title="Test Plan",
        body="Test plan body",
        state="CLOSED",
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
    )

    github_issues = FakeGitHubIssues(issues={42: issue})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=github_issues)

        # Act
        result = runner.invoke(cli, ["retry", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error: Cannot retry closed plan" in result.output

        # Verify no workflow triggered
        assert len(ctx.github.triggered_workflows) == 0


def test_retry_error_missing_plan_label() -> None:
    """Test retrying issue without erk-plan label fails."""
    # Arrange: Create issue missing erk-plan label
    issue = IssueInfo(
        number=42,
        title="Test Issue",
        body="Test issue body",
        state="OPEN",
        url="https://github.com/owner/repo/issues/42",
        labels=["other-label"],  # Missing erk-plan
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
    )

    github_issues = FakeGitHubIssues(issues={42: issue})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=github_issues)

        # Act
        result = runner.invoke(cli, ["retry", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error: Issue is not an erk plan" in result.output

        # Verify no workflow triggered
        assert len(ctx.github.triggered_workflows) == 0


def test_retry_error_issue_not_found() -> None:
    """Test retrying non-existent issue fails."""
    # Arrange: Empty issue store
    github_issues = FakeGitHubIssues(issues={})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=github_issues)

        # Act
        result = runner.invoke(cli, ["retry", "999"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error:" in result.output


def test_retry_with_github_url() -> None:
    """Test retrying with GitHub URL instead of issue number."""
    # Arrange: Create plan issue
    issue = IssueInfo(
        number=42,
        title="Test Plan",
        body="Test plan body",
        state="OPEN",
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
    )

    github_issues = FakeGitHubIssues(issues={42: issue}, comments={42: []})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=github_issues)

        # Act: Use GitHub URL instead of number
        result = runner.invoke(
            cli,
            ["retry", "https://github.com/owner/repo/issues/42"],
            obj=ctx,
        )

        # Assert
        assert result.exit_code == 0
        assert "✓ Plan #42 requeued (retry #1)" in result.output
        assert "View issue: https://github.com/owner/repo/issues/42" in result.output


def test_retry_with_invalid_url() -> None:
    """Test retrying with invalid URL fails with clear error."""
    # Arrange
    github_issues = FakeGitHubIssues(issues={})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=github_issues)

        # Act: Use invalid URL
        result = runner.invoke(
            cli,
            ["retry", "https://example.com/invalid"],
            obj=ctx,
        )

        # Assert
        assert result.exit_code == 1
        assert "Error: Invalid" in result.output
