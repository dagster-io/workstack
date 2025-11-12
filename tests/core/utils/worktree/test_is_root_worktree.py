"""Tests for is_root_worktree function."""

from pathlib import Path

from workstack.core.worktree_utils import is_root_worktree


def test_returns_true_for_root_worktree() -> None:
    """Test identifies root worktree correctly."""
    worktree_path = Path("/repo")
    repo_root = Path("/repo")

    result = is_root_worktree(worktree_path, repo_root)

    assert result is True


def test_returns_false_for_non_root_worktree() -> None:
    """Test identifies non-root worktree correctly."""
    worktree_path = Path("/repo/workstacks/feat")
    repo_root = Path("/repo")

    result = is_root_worktree(worktree_path, repo_root)

    assert result is False


def test_handles_path_normalization() -> None:
    """Test handles different path representations correctly."""
    # Even with trailing slashes or relative paths, should resolve correctly
    worktree_path = Path("/repo/.")
    repo_root = Path("/repo")

    result = is_root_worktree(worktree_path, repo_root)

    assert result is True
