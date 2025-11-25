"""Unit tests for wt list command helper functions."""

from pathlib import Path

from erk_shared.github.types import PullRequestInfo

from erk.cli.commands.wt.list_cmd import (
    _format_pr_cell,
    _get_impl_issue,
    _get_sync_status,
)
from erk.core.git.fake import FakeGit
from tests.fakes.context import create_test_context


def test_get_sync_status_current() -> None:
    """Test sync status returns 'current' when branch is up-to-date."""
    worktree_path = Path("/repo/worktree")
    git = FakeGit(
        ahead_behind={(worktree_path, "feature"): (0, 0)},
    )
    ctx = create_test_context(git=git)

    result = _get_sync_status(ctx, worktree_path, "feature")

    assert result == "current"


def test_get_sync_status_ahead_only() -> None:
    """Test sync status returns 'N↑' when ahead only."""
    worktree_path = Path("/repo/worktree")
    git = FakeGit(
        ahead_behind={(worktree_path, "feature"): (3, 0)},
    )
    ctx = create_test_context(git=git)

    result = _get_sync_status(ctx, worktree_path, "feature")

    assert result == "3↑"


def test_get_sync_status_behind_only() -> None:
    """Test sync status returns 'N↓' when behind only."""
    worktree_path = Path("/repo/worktree")
    git = FakeGit(
        ahead_behind={(worktree_path, "feature"): (0, 2)},
    )
    ctx = create_test_context(git=git)

    result = _get_sync_status(ctx, worktree_path, "feature")

    assert result == "2↓"


def test_get_sync_status_ahead_and_behind() -> None:
    """Test sync status returns 'N↑ M↓' when both ahead and behind."""
    worktree_path = Path("/repo/worktree")
    git = FakeGit(
        ahead_behind={(worktree_path, "feature"): (5, 3)},
    )
    ctx = create_test_context(git=git)

    result = _get_sync_status(ctx, worktree_path, "feature")

    assert result == "5↑ 3↓"


def test_get_sync_status_none_branch() -> None:
    """Test sync status returns '-' when branch is None (detached HEAD)."""
    worktree_path = Path("/repo/worktree")
    git = FakeGit()
    ctx = create_test_context(git=git)

    result = _get_sync_status(ctx, worktree_path, None)

    assert result == "-"


def test_get_impl_issue_from_impl_folder(tmp_path: Path) -> None:
    """Test getting impl issue from .impl/issue.json."""
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    impl_dir = worktree_path / ".impl"
    impl_dir.mkdir()

    # Create plan.md (required for get_impl_path to return path)
    plan_file = impl_dir / "plan.md"
    plan_file.write_text("# Plan", encoding="utf-8")

    # Create issue.json
    issue_file = impl_dir / "issue.json"
    issue_file.write_text(
        '{"issue_number": 42, "issue_url": "https://github.com/owner/repo/issues/42", '
        '"created_at": "2024-01-01T00:00:00Z", "synced_at": "2024-01-01T00:00:00Z"}',
        encoding="utf-8",
    )

    git = FakeGit(existing_paths={plan_file})
    ctx = create_test_context(git=git)

    result = _get_impl_issue(ctx, worktree_path)

    assert result == "#42"


def test_get_impl_issue_from_git_config() -> None:
    """Test getting impl issue from git config fallback."""
    worktree_path = Path("/repo/worktree")
    git = FakeGit(
        current_branches={worktree_path: "feature"},
        branch_issues={"feature": 123},
    )
    ctx = create_test_context(git=git)

    result = _get_impl_issue(ctx, worktree_path)

    assert result == "#123"


def test_get_impl_issue_none_when_not_found() -> None:
    """Test getting impl issue returns None when no issue found."""
    worktree_path = Path("/repo/worktree")
    git = FakeGit(
        current_branches={worktree_path: "feature"},
        # No branch_issues configured
    )
    ctx = create_test_context(git=git)

    result = _get_impl_issue(ctx, worktree_path)

    assert result is None


def test_format_pr_cell_with_pr() -> None:
    """Test formatting PR cell with PR info."""
    pr = PullRequestInfo(
        number=123,
        state="OPEN",
        is_draft=False,
        url="https://github.com/owner/repo/pull/123",
        owner="owner",
        repo="repo",
        title="Add feature",
        checks_passing=None,
    )

    result = _format_pr_cell(pr)

    assert "#123" in result
    assert "👀" in result  # Default open PR emoji


def test_format_pr_cell_with_draft_pr() -> None:
    """Test formatting PR cell with draft PR."""
    pr = PullRequestInfo(
        number=456,
        state="OPEN",
        is_draft=True,
        url="https://github.com/owner/repo/pull/456",
        owner="owner",
        repo="repo",
        title="WIP: Feature",
        checks_passing=None,
    )

    result = _format_pr_cell(pr)

    assert "#456" in result
    assert "🚧" in result  # Draft PR emoji


def test_format_pr_cell_with_merged_pr() -> None:
    """Test formatting PR cell with merged PR."""
    pr = PullRequestInfo(
        number=789,
        state="MERGED",
        is_draft=False,
        url="https://github.com/owner/repo/pull/789",
        owner="owner",
        repo="repo",
        title="Merged feature",
        checks_passing=None,
    )

    result = _format_pr_cell(pr)

    assert "#789" in result
    assert "🎉" in result  # Merged PR emoji


def test_format_pr_cell_none() -> None:
    """Test formatting PR cell with no PR."""
    result = _format_pr_cell(None)

    assert result == "-"
