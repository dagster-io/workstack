"""Unit tests for status data model factory methods."""

from pathlib import Path

from workstack.status.models.status_data import WorktreeDisplayInfo


def test_worktree_display_info_root_factory() -> None:
    """Test WorktreeDisplayInfo.root() factory method."""
    # Arrange
    path = Path("/tmp/repo")

    # Act
    worktree = WorktreeDisplayInfo.root(path)

    # Assert
    assert worktree.path == path
    assert worktree.branch == "main"
    assert worktree.name == "root"
    assert worktree.is_root is True


def test_worktree_display_info_root_factory_custom_branch() -> None:
    """Test WorktreeDisplayInfo.root() with custom branch."""
    # Arrange
    path = Path("/tmp/repo")

    # Act
    worktree = WorktreeDisplayInfo.root(path, branch="master")

    # Assert
    assert worktree.path == path
    assert worktree.branch == "master"
    assert worktree.name == "root"
    assert worktree.is_root is True


def test_worktree_display_info_root_factory_custom_name() -> None:
    """Test WorktreeDisplayInfo.root() with custom name."""
    # Arrange
    path = Path("/tmp/repo")

    # Act
    worktree = WorktreeDisplayInfo.root(path, name="custom-root")

    # Assert
    assert worktree.path == path
    assert worktree.branch == "main"
    assert worktree.name == "custom-root"
    assert worktree.is_root is True


def test_worktree_display_info_feature_factory() -> None:
    """Test WorktreeDisplayInfo.feature() factory method."""
    # Arrange
    path = Path("/tmp/my-feature")

    # Act
    worktree = WorktreeDisplayInfo.feature(path, "feature-branch")

    # Assert
    assert worktree.path == path
    assert worktree.branch == "feature-branch"
    assert worktree.name == "my-feature"  # Uses path.name
    assert worktree.is_root is False


def test_worktree_display_info_feature_factory_custom_name() -> None:
    """Test WorktreeDisplayInfo.feature() with custom name."""
    # Arrange
    path = Path("/tmp/feature-worktree")

    # Act
    worktree = WorktreeDisplayInfo.feature(path, "feature-branch", name="custom-name")

    # Assert
    assert worktree.path == path
    assert worktree.branch == "feature-branch"
    assert worktree.name == "custom-name"
    assert worktree.is_root is False


def test_worktree_display_info_feature_uses_path_name_by_default() -> None:
    """Test WorktreeDisplayInfo.feature() defaults to path.name for display name."""
    # Arrange
    path = Path("/some/long/path/my-worktree-name")

    # Act
    worktree = WorktreeDisplayInfo.feature(path, "branch")

    # Assert
    assert worktree.name == "my-worktree-name"
    assert worktree.is_root is False
