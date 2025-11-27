"""Tests for erk submit command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo
from erk_shared.github.types import PRDetailedInfo

from erk.cli.commands.submit import ERK_PLAN_LABEL, derive_branch_name, submit_cmd
from erk.core.git.fake import FakeGit
from erk.core.github.fake import FakeGitHub
from erk.core.repo_discovery import RepoContext
from tests.fakes.context import create_test_context


def test_submit_valid_issue(tmp_path: Path) -> None:
    """Test submit triggers workflow via direct dispatch on valid issue."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create issue with erk-plan label, OPEN state
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
    assert "Issue submitted successfully!" in result.output
    assert "View workflow run:" in result.output

    # Verify workflow was triggered with correct parameters
    assert len(fake_github.triggered_workflows) == 1
    workflow, inputs = fake_github.triggered_workflows[0]
    assert workflow == "dispatch-erk-queue-git.yml"
    assert inputs["issue_number"] == "123"
    assert inputs["issue_title"] == "Implement feature X"

    # Verify queued comment was posted
    added_comments = fake_github_issues.added_comments
    assert len(added_comments) == 1
    issue_number, comment_body = added_comments[0]
    assert issue_number == 123
    assert "Issue Queued for Implementation" in comment_body
    assert "dispatch-erk-queue-git" in comment_body


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

    # Verify workflow was NOT triggered
    assert len(fake_github.triggered_workflows) == 0


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

    # Verify workflow was NOT triggered
    assert len(fake_github.triggered_workflows) == 0


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


def test_submit_displays_workflow_run_url(tmp_path: Path) -> None:
    """Test submit displays workflow run URL from trigger_workflow response."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create issue with erk-plan label, OPEN state
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
    # FakeGitHub.trigger_workflow() returns "1234567890" by default
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
    assert "Issue submitted successfully!" in result.output
    # Verify workflow run URL is displayed (uses run_id returned by trigger_workflow)
    expected_url = (
        "View workflow run: https://github.com/test-owner/test-repo/actions/runs/1234567890"
    )
    assert expected_url in result.output


def test_submit_requires_gh_authentication(tmp_path: Path) -> None:
    """Test submit fails early if gh CLI is not authenticated (LBYL)."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create valid issue with erk-plan label
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
    # Configure FakeGitHub to simulate unauthenticated state
    fake_github = FakeGitHub(authenticated=False)

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

    # Should fail early with authentication error (LBYL)
    assert result.exit_code == 1
    assert "Error: GitHub CLI (gh) is not authenticated" in result.output
    assert "gh auth login" in result.output

    # Verify workflow was NOT triggered (failure happened before workflow dispatch)
    assert len(fake_github.triggered_workflows) == 0


# Tests for derive_branch_name helper


class TestDeriveBranchName:
    """Tests for the derive_branch_name helper function."""

    def test_simple_title(self) -> None:
        """Test simple title converts to branch name."""
        assert derive_branch_name("Simple Feature") == "simple-feature"

    def test_uppercase_to_lowercase(self) -> None:
        """Test uppercase letters are converted to lowercase."""
        assert derive_branch_name("UPPERCASE TITLE") == "uppercase-title"

    def test_special_characters_to_hyphens(self) -> None:
        """Test special characters are converted to hyphens."""
        assert derive_branch_name("Feature: Add (new) stuff!") == "feature-add-new-stuff"

    def test_multiple_hyphens_collapsed(self) -> None:
        """Test multiple consecutive hyphens are collapsed to one."""
        assert derive_branch_name("A---B   C") == "a-b-c"

    def test_leading_trailing_hyphens_removed(self) -> None:
        """Test leading and trailing hyphens are removed."""
        assert derive_branch_name("---title---") == "title"

    def test_truncation_to_30_chars(self) -> None:
        """Test branch name is truncated to 30 characters."""
        result = derive_branch_name("This is a very long issue title that exceeds 30 chars")
        assert len(result) <= 30
        assert result == "this-is-a-very-long-issue-titl"

    def test_trailing_hyphen_removed_after_truncation(self) -> None:
        """Test trailing hyphen is removed after truncation."""
        # Create a title that when truncated at 30 chars ends with hyphen
        # "Convert SystemExit to Ensure Call" -> "convert-systemexit-to-ensure-c"
        result = derive_branch_name("Convert SystemExit to Ensure Call")
        assert result == "convert-systemexit-to-ensure-c"
        assert not result.endswith("-")

    def test_empty_title(self) -> None:
        """Test empty title produces empty string."""
        assert derive_branch_name("") == ""

    def test_numbers_preserved(self) -> None:
        """Test numbers are preserved in branch name."""
        assert derive_branch_name("Issue 123 Fix") == "issue-123-fix"


# Tests for PR state validation


def test_submit_rejects_closed_pr(tmp_path: Path) -> None:
    """Test submit fails when PR for derived branch is CLOSED."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    issue = IssueInfo(
        number=456,
        title="My Feature",  # Will derive branch name "my-feature"
        body="# Plan\n\nImplementation...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/456",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    # Set up PR as CLOSED for this branch
    fake_github_issues = FakeGitHubIssues(issues={456: issue})
    fake_git = FakeGit()
    fake_github = FakeGitHub(
        pr_detailed_infos={
            "my-feature": PRDetailedInfo(
                number=100,
                state="CLOSED",
                linked_issue_number=456,
                branch_name="my-feature",
            )
        }
    )

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

    assert result.exit_code == 1
    assert "PR for branch 'my-feature' is CLOSED" in result.output
    assert "Cannot submit to a closed PR" in result.output
    assert "gh pr reopen my-feature" in result.output
    assert "git push origin --delete my-feature" in result.output

    # Verify workflow was NOT triggered
    assert len(fake_github.triggered_workflows) == 0


def test_submit_rejects_merged_pr(tmp_path: Path) -> None:
    """Test submit fails when PR for derived branch is MERGED."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    issue = IssueInfo(
        number=789,
        title="Another Feature",  # Will derive branch name "another-feature"
        body="# Plan\n\nImplementation...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/789",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    # Set up PR as MERGED for this branch
    fake_github_issues = FakeGitHubIssues(issues={789: issue})
    fake_git = FakeGit()
    fake_github = FakeGitHub(
        pr_detailed_infos={
            "another-feature": PRDetailedInfo(
                number=200,
                state="MERGED",
                linked_issue_number=789,
                branch_name="another-feature",
            )
        }
    )

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
    result = runner.invoke(submit_cmd, ["789"], obj=ctx)

    assert result.exit_code == 1
    assert "PR for branch 'another-feature' is MERGED" in result.output
    assert "Cannot submit to a merged PR" in result.output

    # Verify workflow was NOT triggered
    assert len(fake_github.triggered_workflows) == 0


def test_submit_rejects_branch_collision(tmp_path: Path) -> None:
    """Test submit fails when branch is associated with different issue."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    # Issue 555 with title that derives same branch as existing PR for issue 444
    issue = IssueInfo(
        number=555,
        title="Convert SystemExit to Ensure C",  # Will derive "convert-systemexit-to-ensure-c"
        body="# Plan\n\nImplementation...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/555",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    # Set up PR as belonging to DIFFERENT issue (444)
    fake_github_issues = FakeGitHubIssues(issues={555: issue})
    fake_git = FakeGit()
    fake_github = FakeGitHub(
        pr_detailed_infos={
            "convert-systemexit-to-ensure-c": PRDetailedInfo(
                number=300,
                state="CLOSED",  # State doesn't matter, collision is checked first
                linked_issue_number=444,  # Different issue!
                branch_name="convert-systemexit-to-ensure-c",
            )
        }
    )

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
    result = runner.invoke(submit_cmd, ["555"], obj=ctx)

    assert result.exit_code == 1
    assert "Branch 'convert-systemexit-to-ensure-c' is associated with issue #444" in result.output
    assert "This issue (#555) would derive the same branch name" in result.output
    assert "Please rename one of the issues" in result.output

    # Verify workflow was NOT triggered
    assert len(fake_github.triggered_workflows) == 0


def test_submit_allows_open_pr_same_issue(tmp_path: Path) -> None:
    """Test submit allows OPEN PR linked to the same issue."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    issue = IssueInfo(
        number=999,
        title="Existing Feature",  # Will derive branch name "existing-feature"
        body="# Plan\n\nImplementation...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/999",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    # Set up PR as OPEN and linked to SAME issue
    fake_github_issues = FakeGitHubIssues(issues={999: issue})
    fake_git = FakeGit()
    fake_github = FakeGitHub(
        pr_detailed_infos={
            "existing-feature": PRDetailedInfo(
                number=400,
                state="OPEN",
                linked_issue_number=999,  # Same issue - allowed
                branch_name="existing-feature",
            )
        }
    )

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

    # Should succeed
    assert result.exit_code == 0
    assert "Issue submitted successfully!" in result.output

    # Verify workflow was triggered
    assert len(fake_github.triggered_workflows) == 1


def test_submit_allows_no_existing_pr(tmp_path: Path) -> None:
    """Test submit succeeds when no PR exists for the derived branch."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    issue = IssueInfo(
        number=111,
        title="Brand New Feature",  # Will derive branch name "brand-new-feature"
        body="# Plan\n\nImplementation...",
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/111",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

    # No pr_detailed_infos configured - get_pr_for_branch returns None
    fake_github_issues = FakeGitHubIssues(issues={111: issue})
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
    result = runner.invoke(submit_cmd, ["111"], obj=ctx)

    # Should succeed
    assert result.exit_code == 0
    assert "Issue submitted successfully!" in result.output

    # Verify workflow was triggered
    assert len(fake_github.triggered_workflows) == 1
