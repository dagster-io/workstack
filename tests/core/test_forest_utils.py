"""Tests for forest business logic utilities."""

import pytest

from erk.core.forest_types import Forest, ForestMetadata
from erk.core.forest_utils import (
    add_worktree_to_forest,
    create_forest,
    find_forest_by_worktree,
    get_empty_forests,
    remove_worktree_from_forest,
    rename_forest,
    validate_forest_name,
)


def test_create_forest_basic() -> None:
    """Test basic forest creation."""
    forest = create_forest(
        name="my-forest",
        worktrees=["wt1", "wt2"],
        root_branch="main",
        created_at="2025-01-01T00:00:00Z",
    )

    assert forest.name == "my-forest"
    assert forest.worktrees == ["wt1", "wt2"]
    assert forest.root_branch == "main"
    assert forest.created_at == "2025-01-01T00:00:00Z"


def test_create_forest_auto_timestamp() -> None:
    """Test forest creation with automatic timestamp."""
    forest = create_forest(name="my-forest", worktrees=["wt1"], root_branch="main")

    # Should have ISO 8601 timestamp
    assert "T" in forest.created_at
    assert forest.created_at.endswith("Z") or "+" in forest.created_at


def test_create_forest_invalid_name() -> None:
    """Test forest creation with invalid name."""
    with pytest.raises(ValueError, match="Invalid forest name"):
        create_forest(name="", worktrees=["wt1"], root_branch="main")


def test_add_worktree_to_forest() -> None:
    """Test adding worktree to forest (immutable)."""
    original = Forest(
        name="my-forest",
        worktrees=["wt1"],
        created_at="2025-01-01T00:00:00Z",
        root_branch="main",
    )

    updated = add_worktree_to_forest(original, "wt2")

    # Original unchanged (immutable)
    assert original.worktrees == ["wt1"]

    # Updated has new worktree
    assert updated.worktrees == ["wt1", "wt2"]
    assert updated.name == original.name
    assert updated.created_at == original.created_at


def test_add_worktree_already_present() -> None:
    """Test adding worktree that already exists."""
    original = Forest(
        name="my-forest",
        worktrees=["wt1"],
        created_at="2025-01-01T00:00:00Z",
        root_branch="main",
    )

    updated = add_worktree_to_forest(original, "wt1")

    # Should return same forest (no duplicate)
    assert updated is original


def test_remove_worktree_from_forest() -> None:
    """Test removing worktree from forest (immutable)."""
    original = Forest(
        name="my-forest",
        worktrees=["wt1", "wt2", "wt3"],
        created_at="2025-01-01T00:00:00Z",
        root_branch="main",
    )

    updated = remove_worktree_from_forest(original, "wt2")

    # Original unchanged
    assert original.worktrees == ["wt1", "wt2", "wt3"]

    # Updated has worktree removed
    assert updated.worktrees == ["wt1", "wt3"]
    assert updated.name == original.name


def test_remove_worktree_not_present() -> None:
    """Test removing worktree that doesn't exist."""
    original = Forest(
        name="my-forest",
        worktrees=["wt1"],
        created_at="2025-01-01T00:00:00Z",
        root_branch="main",
    )

    updated = remove_worktree_from_forest(original, "wt2")

    # Should return same forest (nothing to remove)
    assert updated is original


def test_find_forest_by_worktree_found() -> None:
    """Test finding forest containing worktree."""
    metadata = ForestMetadata(
        forests={
            "forest1": Forest(
                name="forest1",
                worktrees=["wt1", "wt2"],
                created_at="2025-01-01T00:00:00Z",
                root_branch="main",
            ),
            "forest2": Forest(
                name="forest2",
                worktrees=["wt3", "wt4"],
                created_at="2025-01-01T00:00:00Z",
                root_branch="main",
            ),
        }
    )

    forest = find_forest_by_worktree(metadata, "wt3")

    assert forest is not None
    assert forest.name == "forest2"


def test_find_forest_by_worktree_not_found() -> None:
    """Test finding worktree not in any forest."""
    metadata = ForestMetadata(
        forests={
            "forest1": Forest(
                name="forest1",
                worktrees=["wt1", "wt2"],
                created_at="2025-01-01T00:00:00Z",
                root_branch="main",
            ),
        }
    )

    forest = find_forest_by_worktree(metadata, "wt99")

    assert forest is None


def test_rename_forest() -> None:
    """Test renaming a forest."""
    metadata = ForestMetadata(
        forests={
            "old-name": Forest(
                name="old-name",
                worktrees=["wt1", "wt2"],
                created_at="2025-01-01T00:00:00Z",
                root_branch="main",
            ),
            "other": Forest(
                name="other",
                worktrees=["wt3"],
                created_at="2025-01-01T00:00:00Z",
                root_branch="main",
            ),
        }
    )

    updated = rename_forest(metadata, "old-name", "new-name")

    # Original unchanged
    assert "old-name" in metadata.forests

    # Updated has renamed forest
    assert "new-name" in updated.forests
    assert "old-name" not in updated.forests
    assert updated.forests["new-name"].worktrees == ["wt1", "wt2"]
    assert "other" in updated.forests


def test_rename_forest_not_found() -> None:
    """Test renaming non-existent forest."""
    metadata = ForestMetadata(forests={})

    with pytest.raises(ValueError, match="does not exist"):
        rename_forest(metadata, "nonexistent", "new-name")


def test_rename_forest_name_conflict() -> None:
    """Test renaming to existing forest name."""
    metadata = ForestMetadata(
        forests={
            "forest1": Forest(
                name="forest1",
                worktrees=["wt1"],
                created_at="2025-01-01T00:00:00Z",
                root_branch="main",
            ),
            "forest2": Forest(
                name="forest2",
                worktrees=["wt2"],
                created_at="2025-01-01T00:00:00Z",
                root_branch="main",
            ),
        }
    )

    with pytest.raises(ValueError, match="already exists"):
        rename_forest(metadata, "forest1", "forest2")


def test_get_empty_forests() -> None:
    """Test identifying empty forests."""
    metadata = ForestMetadata(
        forests={
            "empty1": Forest(
                name="empty1",
                worktrees=["wt1", "wt2"],
                created_at="2025-01-01T00:00:00Z",
                root_branch="main",
            ),
            "full": Forest(
                name="full",
                worktrees=["wt3", "wt4"],
                created_at="2025-01-01T00:00:00Z",
                root_branch="main",
            ),
            "empty2": Forest(
                name="empty2",
                worktrees=["wt5"],
                created_at="2025-01-01T00:00:00Z",
                root_branch="main",
            ),
        }
    )

    existing_worktrees = ["wt3", "wt4"]  # Only wt3 and wt4 exist
    empty = get_empty_forests(metadata, existing_worktrees)

    assert set(empty) == {"empty1", "empty2"}


def test_get_empty_forests_none_empty() -> None:
    """Test when no forests are empty."""
    metadata = ForestMetadata(
        forests={
            "forest1": Forest(
                name="forest1",
                worktrees=["wt1"],
                created_at="2025-01-01T00:00:00Z",
                root_branch="main",
            ),
        }
    )

    empty = get_empty_forests(metadata, ["wt1"])

    assert empty == []


def test_validate_forest_name_valid() -> None:
    """Test valid forest names."""
    assert validate_forest_name("my-forest") is True
    assert validate_forest_name("forest123") is True
    assert validate_forest_name("a") is True
    assert validate_forest_name("a-b-c-1-2-3") is True


def test_validate_forest_name_invalid() -> None:
    """Test invalid forest names."""
    # Empty
    assert validate_forest_name("") is False

    # Too long
    assert validate_forest_name("a" * 31) is False

    # Invalid characters
    assert validate_forest_name("my_forest") is False
    assert validate_forest_name("my forest") is False
    assert validate_forest_name("my.forest") is False
    assert validate_forest_name("my/forest") is False


def test_validate_forest_name_max_length() -> None:
    """Test forest name at max length."""
    # Exactly 30 chars should be valid
    assert validate_forest_name("a" * 30) is True

    # 31 chars should be invalid
    assert validate_forest_name("a" * 31) is False
