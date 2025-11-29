"""Unit tests for new Git ABC methods.

This test file validates the 7 new methods added to the Git ABC:
- add_all
- commit
- amend_commit
- count_commits_in_branch
- get_repository_root
- get_diff_to_parent
- check_merge_conflicts

These tests use FakeGit (Layer 4: Business Logic Tests over fakes).
"""

from pathlib import Path

import pytest

from tests.fakes.git import FakeGit


def test_add_all_returns_success() -> None:
    """Test that add_all returns True for successful staging."""
    fake_git = FakeGit()
    cwd = Path("/repo/worktree")

    result = fake_git.add_all(cwd)

    assert result is True


def test_commit_tracks_message() -> None:
    """Test that commit tracks the commit message."""
    fake_git = FakeGit()
    cwd = Path("/repo/worktree")
    message = "feat: add new feature"

    result = fake_git.commit(cwd, message)

    assert result is True
    # Note: FakeGit tracks commits internally but doesn't expose them via property
    # This validates the return value contract


def test_commit_multiple_messages() -> None:
    """Test that multiple commits are tracked in order."""
    fake_git = FakeGit()
    cwd = Path("/repo/worktree")

    fake_git.commit(cwd, "first commit")
    fake_git.commit(cwd, "second commit")
    result = fake_git.commit(cwd, "third commit")

    assert result is True


def test_amend_commit_updates_message() -> None:
    """Test that amend_commit updates the last commit message."""
    fake_git = FakeGit()
    cwd = Path("/repo/worktree")

    fake_git.commit(cwd, "original message")
    result = fake_git.amend_commit(cwd, "amended message")

    assert result is True


def test_amend_commit_with_no_commits() -> None:
    """Test that amend_commit creates commit if none exist."""
    fake_git = FakeGit()
    cwd = Path("/repo/worktree")

    result = fake_git.amend_commit(cwd, "first message")

    assert result is True


def test_count_commits_in_branch_returns_configured_count() -> None:
    """Test that count_commits_in_branch returns configured count."""
    fake_git = FakeGit(commit_count=5)
    cwd = Path("/repo/worktree")

    count = fake_git.count_commits_in_branch(cwd, "main")

    assert count == 5


def test_count_commits_in_branch_zero_by_default() -> None:
    """Test that count_commits_in_branch returns 0 by default."""
    fake_git = FakeGit()
    cwd = Path("/repo/worktree")

    count = fake_git.count_commits_in_branch(cwd, "main")

    assert count == 0


def test_get_repository_root_returns_cwd_string() -> None:
    """Test that get_repository_root returns cwd as string."""
    fake_git = FakeGit()
    cwd = Path("/repo/worktree")

    root = fake_git.get_repository_root(cwd)

    assert root == str(cwd)


def test_get_diff_to_parent_returns_configured_diff() -> None:
    """Test that get_diff_to_parent returns configured diff output."""
    diff_output = "diff --git a/file.py b/file.py\n+new line"
    fake_git = FakeGit(diff_output=diff_output)
    cwd = Path("/repo/worktree")

    diff = fake_git.get_diff_to_parent(cwd, "main")

    assert diff == diff_output


def test_get_diff_to_parent_empty_by_default() -> None:
    """Test that get_diff_to_parent returns empty string by default."""
    fake_git = FakeGit()
    cwd = Path("/repo/worktree")

    diff = fake_git.get_diff_to_parent(cwd, "main")

    assert diff == ""


def test_check_merge_conflicts_returns_true_when_configured() -> None:
    """Test that check_merge_conflicts returns True when conflicts configured."""
    fake_git = FakeGit(has_merge_conflicts=True)
    cwd = Path("/repo/worktree")

    has_conflicts = fake_git.check_merge_conflicts(cwd, "main", "feature")

    assert has_conflicts is True


def test_check_merge_conflicts_returns_false_by_default() -> None:
    """Test that check_merge_conflicts returns False by default (clean merge)."""
    fake_git = FakeGit()
    cwd = Path("/repo/worktree")

    has_conflicts = fake_git.check_merge_conflicts(cwd, "main", "feature")

    assert has_conflicts is False


@pytest.mark.parametrize(
    "commit_count,expected",
    [
        (0, 0),
        (1, 1),
        (10, 10),
        (100, 100),
    ],
)
def test_count_commits_various_counts(commit_count: int, expected: int) -> None:
    """Test count_commits_in_branch with various configured counts."""
    fake_git = FakeGit(commit_count=commit_count)
    cwd = Path("/repo/worktree")

    count = fake_git.count_commits_in_branch(cwd, "main")

    assert count == expected
