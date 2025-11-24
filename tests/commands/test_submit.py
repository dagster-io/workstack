"""Tests for erk submit command."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo

from erk.cli.commands.submit import ERK_PLAN_LABEL, ERK_QUEUE_LABEL, submit_cmd
from erk.core.git.fake import FakeGit
from erk.core.github.fake import FakeGitHub
from erk.core.repo_discovery import RepoContext
from tests.fakes.context import create_test_context


@pytest.mark.skip(reason="TODO: Update for new workflow with .erp/ folder and draft PR creation")
def test_submit_valid_issue(tmp_path: Path) -> None:
    """Test submit ensures erk-queue label on valid issue."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create issue with erk-plan label, OPEN state, no erk-queue
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body="# Plan\n\nImplementation details...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    fake_git = FakeGit()
    fake_github = FakeGitHub()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0
    assert "Issue submitted!" in result.output
    assert "GitHub Actions will begin implementation automatically" in result.output

    # Verify label was added
    updated_issue = fake_github_issues.get_issue(repo_root, 123)
    assert ERK_QUEUE_LABEL in updated_issue.labels
    assert ERK_PLAN_LABEL in updated_issue.labels

    # Verify queued comment was posted
    added_comments = fake_github_issues.added_comments
    assert len(added_comments) == 1
    issue_number, comment_body = added_comments[0]
    assert issue_number == 123
    assert "Issue Queued for Implementation" in comment_body
    assert "submission-queued" in comment_body
    assert "dispatch-erk-queue" in comment_body


def test_submit_missing_erk_plan_label(tmp_path: Path) -> None:
    """Test submit rejects issue without erk-plan label."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create issue WITHOUT erk-plan label
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Regular issue",
        body="Not a plan issue",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=["bug"],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    fake_git = FakeGit()
    fake_github = FakeGitHub()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 1
    assert "does not have erk-plan label" in result.output
    assert "Cannot submit non-plan issues" in result.output

    # Verify label was NOT added
    updated_issue = fake_github_issues.get_issue(repo_root, 123)
    assert ERK_QUEUE_LABEL not in updated_issue.labels


def test_submit_already_queued(tmp_path: Path) -> None:
    """Test submit rejects issue that already has erk-queue label."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create issue with BOTH erk-plan and erk-queue labels
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body="# Plan\n\nImplementation details...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL, ERK_QUEUE_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    fake_git = FakeGit()
    fake_github = FakeGitHub()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 1
    assert "already has erk-queue label" in result.output
    assert "already been submitted" in result.output


def test_submit_closed_issue(tmp_path: Path) -> None:
    """Test submit rejects closed issues."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create CLOSED issue with erk-plan label
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body="# Plan\n\nImplementation details...",
        state="CLOSED",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    fake_git = FakeGit()
    fake_github = FakeGitHub()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 1
    assert "is CLOSED" in result.output
    assert "Cannot submit closed issues" in result.output

    # Verify label was NOT added
    updated_issue = fake_github_issues.get_issue(repo_root, 123)
    assert ERK_QUEUE_LABEL not in updated_issue.labels


def test_submit_issue_not_found(tmp_path: Path) -> None:
    """Test submit handles missing issue gracefully."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Empty issues dict - issue 999 doesn't exist
    fake_github_issues = FakeGitHubIssues(issues={})
    fake_git = FakeGit()
    fake_github = FakeGitHub()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["999"], obj=ctx)

    # Should fail with RuntimeError from get_issue
    assert result.exit_code != 0
    assert "Issue #999 not found" in result.output


@pytest.mark.skip(reason="TODO: Update for new workflow with .erp/ folder and draft PR creation")
def test_submit_dry_run(tmp_path: Path) -> None:
    """Test dry-run shows what would happen without making changes."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create valid issue
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Implement feature X",
        body="# Plan\n\nImplementation details...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    fake_git = FakeGit()
    fake_github = FakeGitHub()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123", "--dry-run"], obj=ctx)

    assert result.exit_code == 0
    assert "(dry run)" in result.output
    assert "Would add label: erk-queue" in result.output
    assert "Would trigger GitHub Actions workflow" in result.output

    # Verify label was NOT added in dry-run mode
    updated_issue = fake_github_issues.get_issue(repo_root, 123)
    assert ERK_QUEUE_LABEL not in updated_issue.labels
    assert ERK_PLAN_LABEL in updated_issue.labels


@pytest.mark.skip(reason="TODO: Update for new workflow with .erp/ folder and draft PR creation")
def test_submit_fake_integration(tmp_path: Path) -> None:
    """Test that FakeGitHubIssues correctly adds label to in-memory issue."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create issue
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=456,
        title="Another feature",
        body="# Plan\n\nMore details...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/456",
        labels=[ERK_PLAN_LABEL, "enhancement"],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    fake_github_issues = FakeGitHubIssues(issues={456: issue})
    fake_git = FakeGit()
    fake_github = FakeGitHub()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["456"], obj=ctx)

    assert result.exit_code == 0

    # Verify FakeGitHubIssues correctly maintains all labels
    updated_issue = fake_github_issues.get_issue(repo_root, 456)
    assert ERK_QUEUE_LABEL in updated_issue.labels
    assert ERK_PLAN_LABEL in updated_issue.labels
    assert "enhancement" in updated_issue.labels
    assert len(updated_issue.labels) == 3


@pytest.mark.skip(reason="TODO: Update for new workflow with .erp/ folder and draft PR creation")
def test_submit_displays_workflow_run_url_when_found(tmp_path: Path) -> None:
    """Test submit displays workflow run URL when polling succeeds."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create issue with erk-plan label, OPEN state, no erk-queue
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Add workflow run URL to erk submit output",
        body="# Plan\n\nImplementation details...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    fake_git = FakeGit()
    # Configure fake to return a run ID
    fake_github = FakeGitHub(polled_run_id="1234567890")

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0
    assert "Issue submitted successfully!" in result.output
    # Verify workflow run URL is displayed
    expected_url = (
        "View workflow run: https://github.com/test-owner/test-repo/actions/runs/1234567890"
    )
    assert expected_url in result.output
    # Verify polling was attempted with correct parameters
    assert len(fake_github.poll_attempts) == 1
    workflow, branch_name, timeout, poll_interval = fake_github.poll_attempts[0]
    assert workflow == "dispatch-erk-queue.yml"
    assert branch_name == "add-workflow-run-url-to-erk"  # Derived from title
    assert timeout == 30
    assert poll_interval == 2


@pytest.mark.skip(reason="TODO: Update for new workflow with .erp/ folder and draft PR creation")
def test_submit_displays_fallback_when_polling_times_out(tmp_path: Path) -> None:
    """Test submit displays explicit fallback message when polling times out."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create issue with erk-plan label, OPEN state, no erk-queue
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Test timeout handling",
        body="# Plan\n\nImplementation details...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    fake_git = FakeGit()
    # Configure fake to return None (timeout)
    fake_github = FakeGitHub(polled_run_id=None)

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0
    assert "Issue submitted successfully!" in result.output
    # Verify explicit fallback message is displayed
    assert "(workflow run URL will be available shortly)" in result.output
    # Verify run URL is NOT displayed
    assert "actions/runs/" not in result.output
    # Verify polling was attempted
    assert len(fake_github.poll_attempts) == 1


@pytest.mark.skip(reason="TODO: Update for new workflow with .erp/ folder and draft PR creation")
def test_submit_fake_github_does_not_sleep(tmp_path: Path) -> None:
    """Test that FakeGitHub polling returns immediately without sleeping."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create issue
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=123,
        title="Performance test",
        body="# Plan\n\nImplementation details...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue})
    fake_git = FakeGit()
    fake_github = FakeGitHub(polled_run_id="9999999999")

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        repo=repo,
    )

    runner = CliRunner()
    # This should complete very quickly (< 1 second) if fake doesn't sleep
    import time

    start = time.time()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)
    elapsed = time.time() - start

    assert result.exit_code == 0
    # Verify test completes quickly (< 5 seconds, should be ~instant)
    assert elapsed < 5.0, f"Test took {elapsed:.2f}s, fake should not sleep"
