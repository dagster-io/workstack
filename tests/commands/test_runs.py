"""CLI tests for erk runs command.

This file focuses on CLI-specific concerns for the runs command:
- Command execution and exit codes
- Output formatting and display (status indicators, Rich table)
- Run-centric view with plan/PR linkage
- display_title parsing for issue number extraction

The integration layer (list_workflow_runs) is tested in:
- tests/unit/fakes/test_fake_github.py - Fake infrastructure tests
- tests/integration/test_real_github.py - Real implementation tests

This file trusts that unit layer and only tests CLI integration.
"""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.abc import WorktreeInfo
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.types import PullRequestInfo, WorkflowRun

from erk.cli.commands.runs import _extract_issue_number, runs_cmd
from erk.core.git.fake import FakeGit
from erk.core.github.fake import FakeGitHub
from tests.fakes.context import create_test_context

# ============================================================================
# Unit tests for _extract_issue_number helper
# ============================================================================


def test_extract_issue_number_new_format() -> None:
    """Test parsing new format: '123:abc456' → 123."""
    assert _extract_issue_number("123:abc456") == 123
    assert _extract_issue_number("1:x") == 1
    assert _extract_issue_number("999:distinct-id-here") == 999


def test_extract_issue_number_old_format_returns_none() -> None:
    """Test old format: 'Issue title [abc123]' → None."""
    # Old format has title first, then distinct_id in brackets
    assert _extract_issue_number("Add user authentication [abc123]") is None
    assert _extract_issue_number("Fix bug in parser [xyz789]") is None


def test_extract_issue_number_with_colon_in_title_returns_none() -> None:
    """Test titles with colons but non-numeric prefix → None."""
    # These look like they have colons but the prefix isn't a number
    assert _extract_issue_number("Feature: Add caching [abc]") is None
    assert _extract_issue_number("Bug fix: memory leak [xyz]") is None


def test_extract_issue_number_none_or_empty() -> None:
    """Test None or empty string → None."""
    assert _extract_issue_number(None) is None
    assert _extract_issue_number("") is None


def test_extract_issue_number_no_colon() -> None:
    """Test string without colon → None."""
    assert _extract_issue_number("no colon here") is None
    assert _extract_issue_number("12345") is None


def test_extract_issue_number_whitespace() -> None:
    """Test handling of whitespace."""
    assert _extract_issue_number(" 123:abc") == 123
    assert _extract_issue_number("123 :abc") == 123


# ============================================================================
# CLI tests for runs command
# ============================================================================


def test_runs_cmd_empty_state(tmp_path: Path) -> None:
    """Test runs command displays message when no runs found."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    github_ops = FakeGitHub(workflow_runs=[])  # Empty runs
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    assert "No workflow runs found" in result.output


def test_runs_cmd_single_success_run_with_issue_linkage(tmp_path: Path) -> None:
    """Test runs command displays single successful run with plan linkage."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    now = datetime.now(UTC)
    workflow_runs = [
        WorkflowRun(
            run_id="1234567890",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:abc456",  # New format: issue_number:distinct_id
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)

    # Create issue for linkage
    issues = {
        142: IssueInfo(
            number=142,
            title="Add user authentication with OAuth2",
            body="Plan content",
            state="OPEN",
            url="https://github.com/owner/repo/issues/142",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
        ),
    }
    issues_ops = FakeGitHubIssues(issues=issues)

    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # Check for Rich table output - run_id should appear
    assert "1234567890" in result.output
    # Check for issue linkage
    assert "#142" in result.output
    # Check for title (or truncated version)
    assert "Add user authentication" in result.output
    # Success status indicator
    assert "Success" in result.output or "✅" in result.output


def test_runs_cmd_multiple_runs_different_statuses(tmp_path: Path) -> None:
    """Test runs command displays multiple runs with different statuses."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    now = datetime.now(UTC)
    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:abc",
        ),
        WorkflowRun(
            run_id="456",
            status="completed",
            conclusion="failure",
            branch="feat-2",
            head_sha="def456",
            display_title="143:def",
        ),
        WorkflowRun(
            run_id="789",
            status="in_progress",
            conclusion=None,
            branch="feat-3",
            head_sha="ghi789",
            display_title="144:ghi",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)

    # Create issues for linkage
    issues = {
        142: IssueInfo(
            number=142,
            title="Feature one",
            body="",
            state="OPEN",
            url="https://github.com/owner/repo/issues/142",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
        ),
        143: IssueInfo(
            number=143,
            title="Feature two",
            body="",
            state="OPEN",
            url="https://github.com/owner/repo/issues/143",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
        ),
        144: IssueInfo(
            number=144,
            title="Feature three",
            body="",
            state="OPEN",
            url="https://github.com/owner/repo/issues/144",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
        ),
    }
    issues_ops = FakeGitHubIssues(issues=issues)

    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # All run IDs should appear
    assert "123" in result.output
    assert "456" in result.output
    assert "789" in result.output
    # All issue numbers should appear
    assert "#142" in result.output
    assert "#143" in result.output
    assert "#144" in result.output


def test_runs_cmd_run_without_issue_linkage(tmp_path: Path) -> None:
    """Test runs command handles runs without valid issue linkage (old format)."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            # Old format - no issue linkage possible
            display_title="Add user authentication [abc123]",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    issues_ops = FakeGitHubIssues(issues={})

    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # Run ID should still appear
    assert "123" in result.output
    # Should show "X" for plan/title/pr/chks columns since legacy format can't be parsed
    # (distinguishes "can't parse" from "no data available" which uses "-")
    assert "X" in result.output


def test_runs_cmd_with_pr_linkage(tmp_path: Path) -> None:
    """Test runs command displays PR information when linked."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    now = datetime.now(UTC)
    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:abc456",
        ),
    ]

    # PR linked to issue 142
    pr_info = PullRequestInfo(
        number=201,
        state="OPEN",
        url="https://github.com/owner/repo/pull/201",
        is_draft=False,
        title="Add user auth",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    github_ops = FakeGitHub(
        workflow_runs=workflow_runs,
        pr_issue_linkages={142: [pr_info]},
    )

    issues = {
        142: IssueInfo(
            number=142,
            title="Add user authentication",
            body="",
            state="OPEN",
            url="https://github.com/owner/repo/issues/142",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
        ),
    }
    issues_ops = FakeGitHubIssues(issues=issues)

    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # PR number should appear
    assert "#201" in result.output
    # Checks emoji should appear (✅ for passing)
    assert "✅" in result.output


def test_runs_cmd_handles_queued_status(tmp_path: Path) -> None:
    """Test runs command displays queued status correctly."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    now = datetime.now(UTC)
    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="queued",
            conclusion=None,
            branch="feat-1",
            head_sha="abc123",
            display_title="142:abc",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)

    issues = {
        142: IssueInfo(
            number=142,
            title="Queued feature",
            body="",
            state="OPEN",
            url="https://github.com/owner/repo/issues/142",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
        ),
    }
    issues_ops = FakeGitHubIssues(issues=issues)

    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # Queued status indicator
    assert "Queued" in result.output or "⧗" in result.output


def test_runs_cmd_handles_cancelled_status(tmp_path: Path) -> None:
    """Test runs command displays cancelled status correctly."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    now = datetime.now(UTC)
    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="cancelled",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:abc",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)

    issues = {
        142: IssueInfo(
            number=142,
            title="Cancelled feature",
            body="",
            state="OPEN",
            url="https://github.com/owner/repo/issues/142",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
        ),
    }
    issues_ops = FakeGitHubIssues(issues=issues)

    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # Cancelled status indicator
    assert "Cancelled" in result.output or "⛔" in result.output


def test_runs_cmd_truncates_long_titles(tmp_path: Path) -> None:
    """Test runs command truncates titles longer than 50 characters."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    now = datetime.now(UTC)
    long_title = (
        "This is a very long title that exceeds fifty characters "
        "and should be truncated with ellipsis"
    )

    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
            display_title="142:abc",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)

    issues = {
        142: IssueInfo(
            number=142,
            title=long_title,
            body="",
            state="OPEN",
            url="https://github.com/owner/repo/issues/142",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
        ),
    }
    issues_ops = FakeGitHubIssues(issues=issues)

    ctx = create_test_context(git=git_ops, github=github_ops, issues=issues_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # Full title should NOT appear (it's too long)
    assert long_title not in result.output
    # Truncated version should appear with ellipsis
    assert "..." in result.output
    # Start of title should appear
    assert "This is a very long" in result.output


# ============================================================================
# Tests for logs subcommand (unchanged from original)
# ============================================================================


def test_runs_logs_explicit_run_id(tmp_path: Path) -> None:
    """Test viewing logs with explicit run ID."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    github_ops = FakeGitHub(run_logs={"12345": "Step 1: Setup\nStep 2: Tests\n"})
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, ["logs", "12345"], obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    assert "Step 1: Setup" in result.output
    assert "Step 2: Tests" in result.output


def test_runs_logs_auto_detect(tmp_path: Path) -> None:
    """Test auto-detecting most recent run for current branch."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="feature-x")]},
        current_branches={repo_root: "feature-x"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    workflow_runs = [
        WorkflowRun(
            run_id="111",
            status="completed",
            conclusion="success",
            branch="main",
            head_sha="abc",
        ),
        WorkflowRun(
            run_id="222",
            status="completed",
            conclusion="success",
            branch="feature-x",
            head_sha="def",
        ),
    ]
    github_ops = FakeGitHub(
        workflow_runs=workflow_runs, run_logs={"222": "Logs for feature-x run\n"}
    )
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, ["logs"], obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    assert "Showing logs for run 222" in result.output
    assert "Logs for feature-x run" in result.output


def test_runs_logs_run_not_found(tmp_path: Path) -> None:
    """Test error handling when run doesn't exist."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    github_ops = FakeGitHub(run_logs={})  # No logs configured
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, ["logs", "99999"], obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "99999" in result.output


def test_runs_logs_no_runs_for_branch(tmp_path: Path) -> None:
    """Test auto-detect when no runs exist for current branch."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="feature-y")]},
        current_branches={repo_root: "feature-y"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    workflow_runs = [
        WorkflowRun(
            run_id="111",
            status="completed",
            conclusion="success",
            branch="main",
            head_sha="abc",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, ["logs"], obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 1
    assert "No workflow runs found for branch: feature-y" in result.output
