"""Unit tests for forest merge utilities."""

import pytest

from erk.cli.commands.forest.merge_utils import (
    check_uncommitted_changes,
    create_forest_merge_plan,
    identify_removable_worktrees,
)
from erk.core.forest_types import Forest
from tests.fakes.git import FakeGit
from tests.test_utils import sentinel_path


def test_identify_removable_worktrees() -> None:
    """Test identifying worktrees to remove."""
    forest = Forest(
        name="my-forest",
        worktrees=["wt1", "wt2", "wt3"],
        created_at="2025-01-01T00:00:00Z",
        root_branch="main",
    )

    result = identify_removable_worktrees(forest, "wt2")

    assert set(result) == {"wt1", "wt3"}


def test_identify_removable_worktrees_empty() -> None:
    """Test when target is only worktree."""
    forest = Forest(
        name="my-forest",
        worktrees=["wt1"],
        created_at="2025-01-01T00:00:00Z",
        root_branch="main",
    )

    result = identify_removable_worktrees(forest, "wt1")

    assert result == []


def test_create_forest_merge_plan_with_target() -> None:
    """Test creating merge plan with explicit target."""
    forest = Forest(
        name="my-forest",
        worktrees=["wt1", "wt2", "wt3"],
        created_at="2025-01-01T00:00:00Z",
        root_branch="main",
    )

    plan = create_forest_merge_plan(forest, "wt2", None)

    assert plan.forest_name == "my-forest"
    assert plan.target_worktree == "wt2"
    assert set(plan.worktrees_to_remove) == {"wt1", "wt3"}


def test_create_forest_merge_plan_current_worktree() -> None:
    """Test creating merge plan defaulting to current worktree."""
    forest = Forest(
        name="my-forest",
        worktrees=["wt1", "wt2"],
        created_at="2025-01-01T00:00:00Z",
        root_branch="main",
    )

    plan = create_forest_merge_plan(forest, None, "wt1")

    assert plan.target_worktree == "wt1"
    assert plan.worktrees_to_remove == ["wt2"]


def test_create_forest_merge_plan_first_worktree() -> None:
    """Test creating merge plan defaulting to first worktree."""
    forest = Forest(
        name="my-forest",
        worktrees=["wt1", "wt2"],
        created_at="2025-01-01T00:00:00Z",
        root_branch="main",
    )

    plan = create_forest_merge_plan(forest, None, None)

    assert plan.target_worktree == "wt1"


def test_create_forest_merge_plan_invalid_target() -> None:
    """Test creating merge plan with invalid target."""
    forest = Forest(
        name="my-forest",
        worktrees=["wt1", "wt2"],
        created_at="2025-01-01T00:00:00Z",
        root_branch="main",
    )

    with pytest.raises(ValueError, match="not in forest"):
        create_forest_merge_plan(forest, "wt99", None)


def test_check_uncommitted_changes_none() -> None:
    """Test checking uncommitted changes when all clean."""
    worktrees_dir = sentinel_path()
    wt1_path = worktrees_dir / "wt1"
    wt2_path = worktrees_dir / "wt2"

    git_ops = FakeGit(
        file_statuses={},  # No changes
        existing_paths={wt1_path, wt2_path},
    )

    result = check_uncommitted_changes(["wt1", "wt2"], git_ops, worktrees_dir)

    assert result == []


def test_check_uncommitted_changes_some_dirty() -> None:
    """Test checking uncommitted changes with dirty worktrees."""
    worktrees_dir = sentinel_path()
    wt1_path = worktrees_dir / "wt1"
    wt2_path = worktrees_dir / "wt2"

    git_ops = FakeGit(
        file_statuses={
            wt2_path: ([], ["file.txt"], []),  # wt2 has changes
        },
        existing_paths={wt1_path, wt2_path},
    )

    result = check_uncommitted_changes(["wt1", "wt2"], git_ops, worktrees_dir)

    assert result == ["wt2"]


def test_check_uncommitted_changes_nonexistent_worktree() -> None:
    """Test checking when worktree doesn't exist."""
    git_ops = FakeGit(existing_paths=set())
    worktrees_dir = sentinel_path()

    result = check_uncommitted_changes(["nonexistent"], git_ops, worktrees_dir)

    assert result == []
