"""Tests for GitHubAdapter class.

Tests the adapter that bridges GitHub ABC to GitHubGtKit interface.
"""

from pathlib import Path

from erk_shared.github.types import PullRequestInfo
from erk_shared.integrations.gt.fake import FakeGitGtKitOps, GitState
from erk_shared.integrations.gt.github_adapter import GitHubAdapter

from erk.core.github.fake import FakeGitHub


class TestGitHubAdapter:
    """Tests for GitHubAdapter class."""

    def test_get_repo_root_from_git(self) -> None:
        """Adapter should get repo root from git interface."""
        fake_github = FakeGitHub()
        fake_git = FakeGitGtKitOps(GitState(current_branch="feature"))

        adapter = GitHubAdapter(fake_github, fake_git)

        # Should use git's repository root
        repo_root = adapter._get_repo_root()
        assert repo_root == Path("/fake/repo/root")

    def test_get_current_branch_from_git(self) -> None:
        """Adapter should get current branch from git interface."""
        fake_github = FakeGitHub()
        fake_git = FakeGitGtKitOps(GitState(current_branch="my-feature"))

        adapter = GitHubAdapter(fake_github, fake_git)

        assert adapter._get_current_branch() == "my-feature"

    def test_check_auth_status_delegates_to_github(self) -> None:
        """check_auth_status should delegate to wrapped GitHub."""
        fake_github = FakeGitHub(
            authenticated=True,
            auth_username="test-user",
            auth_hostname="github.com",
        )
        fake_git = FakeGitGtKitOps()

        adapter = GitHubAdapter(fake_github, fake_git)

        is_auth, username, hostname = adapter.check_auth_status()
        assert is_auth is True
        assert username == "test-user"
        assert hostname == "github.com"

    def test_check_auth_status_when_not_authenticated(self) -> None:
        """check_auth_status should return False when not authenticated."""
        fake_github = FakeGitHub(authenticated=False)
        fake_git = FakeGitGtKitOps()

        adapter = GitHubAdapter(fake_github, fake_git)

        is_auth, username, hostname = adapter.check_auth_status()
        assert is_auth is False
        assert username is None
        assert hostname is None

    def test_get_graphite_pr_url(self) -> None:
        """get_graphite_pr_url should delegate to wrapped GitHub."""
        fake_github = FakeGitHub()
        fake_git = FakeGitGtKitOps()

        adapter = GitHubAdapter(fake_github, fake_git)

        url = adapter.get_graphite_pr_url(123)
        assert url == "https://app.graphite.com/github/pr/owner/repo/123"

    def test_get_pr_diff(self) -> None:
        """get_pr_diff should delegate to wrapped GitHub."""
        fake_github = FakeGitHub(pr_diffs={42: "custom diff content"})
        fake_git = FakeGitGtKitOps()

        adapter = GitHubAdapter(fake_github, fake_git)

        diff = adapter.get_pr_diff(42)
        assert diff == "custom diff content"

    def test_get_pr_diff_default(self) -> None:
        """get_pr_diff should return default diff when not configured."""
        fake_github = FakeGitHub()
        fake_git = FakeGitGtKitOps()

        adapter = GitHubAdapter(fake_github, fake_git)

        diff = adapter.get_pr_diff(99)
        assert "diff --git" in diff

    def test_get_pr_status_with_existing_pr(self) -> None:
        """get_pr_status should return PR number and URL for existing branch."""
        fake_github = FakeGitHub(
            prs={
                "feature": PullRequestInfo(
                    number=42,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/42",
                    is_draft=False,
                    title="Test PR",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                )
            }
        )
        fake_git = FakeGitGtKitOps()

        adapter = GitHubAdapter(fake_github, fake_git)

        pr_number, url = adapter.get_pr_status("feature")
        assert pr_number == 42
        assert url == "https://github.com/owner/repo/pull/42"

    def test_get_pr_status_with_no_pr(self) -> None:
        """get_pr_status should return None for non-existent branch."""
        fake_github = FakeGitHub()
        fake_git = FakeGitGtKitOps()

        adapter = GitHubAdapter(fake_github, fake_git)

        pr_number, url = adapter.get_pr_status("nonexistent")
        assert pr_number is None
        assert url is None

    def test_update_pr_metadata_with_pr(self) -> None:
        """update_pr_metadata should update current branch's PR."""
        fake_github = FakeGitHub(pr_statuses={"feature": ("OPEN", 42, "Old Title")})
        fake_git = FakeGitGtKitOps(GitState(current_branch="feature"))

        adapter = GitHubAdapter(fake_github, fake_git)

        result = adapter.update_pr_metadata("New Title", "New Body")
        assert result is True
        assert fake_github.updated_pr_metadata == [(42, "New Title", "New Body")]

    def test_update_pr_metadata_without_pr(self) -> None:
        """update_pr_metadata should return False when no PR exists."""
        fake_github = FakeGitHub()
        fake_git = FakeGitGtKitOps(GitState(current_branch="no-pr-branch"))

        adapter = GitHubAdapter(fake_github, fake_git)

        result = adapter.update_pr_metadata("Title", "Body")
        assert result is False

    def test_mark_pr_ready_with_pr(self) -> None:
        """mark_pr_ready should mark current branch's PR as ready."""
        fake_github = FakeGitHub(pr_statuses={"feature": ("OPEN", 42, "Title")})
        fake_git = FakeGitGtKitOps(GitState(current_branch="feature"))

        adapter = GitHubAdapter(fake_github, fake_git)

        result = adapter.mark_pr_ready()
        assert result is True
        assert fake_github.marked_ready_prs == [42]

    def test_mark_pr_ready_without_pr(self) -> None:
        """mark_pr_ready should return False when no PR exists."""
        fake_github = FakeGitHub()
        fake_git = FakeGitGtKitOps(GitState(current_branch="no-pr-branch"))

        adapter = GitHubAdapter(fake_github, fake_git)

        result = adapter.mark_pr_ready()
        assert result is False

    def test_merge_pr_with_pr(self) -> None:
        """merge_pr should merge current branch's PR."""
        fake_github = FakeGitHub(pr_statuses={"feature": ("OPEN", 42, "Title")})
        fake_git = FakeGitGtKitOps(GitState(current_branch="feature"))

        adapter = GitHubAdapter(fake_github, fake_git)

        result = adapter.merge_pr()
        assert result is True
        assert 42 in fake_github.merged_prs

    def test_merge_pr_without_pr(self) -> None:
        """merge_pr should return False when no PR exists."""
        fake_github = FakeGitHub()
        fake_git = FakeGitGtKitOps(GitState(current_branch="no-pr-branch"))

        adapter = GitHubAdapter(fake_github, fake_git)

        result = adapter.merge_pr()
        assert result is False

    def test_get_pr_mergeability(self) -> None:
        """get_pr_mergeability should delegate to wrapped GitHub."""
        from erk_shared.github.types import PRMergeability

        mergeability = PRMergeability(mergeable="CONFLICTING", merge_state_status="DIRTY")
        fake_github = FakeGitHub(pr_mergeability={42: mergeability})
        fake_git = FakeGitGtKitOps()

        adapter = GitHubAdapter(fake_github, fake_git)

        mergeable, merge_state = adapter.get_pr_mergeability(42)
        assert mergeable == "CONFLICTING"
        assert merge_state == "DIRTY"

    def test_get_pr_mergeability_default(self) -> None:
        """get_pr_mergeability should return defaults when not configured."""
        fake_github = FakeGitHub()
        fake_git = FakeGitGtKitOps()

        adapter = GitHubAdapter(fake_github, fake_git)

        mergeable, merge_state = adapter.get_pr_mergeability(99)
        assert mergeable == "MERGEABLE"
        assert merge_state == "CLEAN"
