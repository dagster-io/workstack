"""Unit tests for forest split utilities."""

from erk.cli.commands.forest.split_utils import (
    create_forest_split_plan,
    detect_or_create_forest_name,
    identify_splittable_branches,
)
from erk.core.forest_types import Forest, ForestMetadata
from erk.core.gitops import WorktreeInfo
from tests.test_utils import sentinel_path


def test_identify_splittable_branches_all() -> None:
    """Test identifying all splittable branches."""
    stack = ["main", "feat-1", "feat-2", "feat-3"]
    current = "feat-1"
    trunk = "main"
    existing = [WorktreeInfo(path=sentinel_path(), branch="feat-1", is_root=False)]

    result = identify_splittable_branches(stack, current, trunk, existing, None)

    assert set(result) == {"feat-2", "feat-3"}


def test_identify_splittable_branches_upstack() -> None:
    """Test identifying upstack branches only."""
    stack = ["main", "feat-1", "feat-2", "feat-3"]
    current = "feat-1"
    trunk = "main"
    existing = []

    result = identify_splittable_branches(stack, current, trunk, existing, "up")

    assert result == ["feat-2", "feat-3"]


def test_identify_splittable_branches_downstack() -> None:
    """Test identifying downstack branches only."""
    stack = ["main", "feat-1", "feat-2", "feat-3"]
    current = "feat-2"
    trunk = "main"
    existing = []

    result = identify_splittable_branches(stack, current, trunk, existing, "down")

    assert result == ["feat-1"]


def test_identify_splittable_branches_excludes_existing() -> None:
    """Test that existing worktrees are excluded."""
    stack = ["main", "feat-1", "feat-2", "feat-3"]
    current = "feat-1"
    trunk = "main"
    existing = [
        WorktreeInfo(path=sentinel_path(), branch="feat-2", is_root=False),
        WorktreeInfo(path=sentinel_path(), branch="feat-3", is_root=False),
    ]

    result = identify_splittable_branches(stack, current, trunk, existing, None)

    assert result == []


def test_identify_splittable_branches_excludes_trunk() -> None:
    """Test that trunk branch is excluded."""
    stack = ["main", "feat-1"]
    current = "feat-1"
    trunk = "main"
    existing = []

    result = identify_splittable_branches(stack, current, trunk, existing, None)

    assert result == []


def test_detect_or_create_forest_name_provided() -> None:
    """Test using provided forest name."""
    current = "feat-1"
    metadata = ForestMetadata(forests={})
    provided = "my-forest"

    result = detect_or_create_forest_name(current, metadata, provided)

    assert result == "my-forest"


def test_detect_or_create_forest_name_existing_forest() -> None:
    """Test detecting existing forest."""
    current = "feat-1"
    forest = Forest(
        name="existing-forest",
        worktrees=["feat-1"],
        created_at="2025-01-01T00:00:00Z",
        root_branch="main",
    )
    metadata = ForestMetadata(forests={"existing-forest": forest})
    provided = None

    result = detect_or_create_forest_name(current, metadata, provided)

    assert result == "existing-forest"


def test_detect_or_create_forest_name_use_branch() -> None:
    """Test using current branch name when no forest exists."""
    current = "feat-1"
    metadata = ForestMetadata(forests={})
    provided = None

    result = detect_or_create_forest_name(current, metadata, provided)

    assert result == "feat-1"


def test_create_forest_split_plan() -> None:
    """Test creating complete split plan."""
    stack = ["main", "feat-1", "feat-2"]
    current = "feat-1"
    trunk = "main"
    existing = []
    metadata = ForestMetadata(forests={})

    plan = create_forest_split_plan(stack, current, trunk, existing, None, "my-forest", metadata)

    assert plan.forest_name == "my-forest"
    assert plan.current_branch == "feat-1"
    assert plan.branches_to_split == ["feat-2"]
    assert plan.worktrees_to_create == ["feat-2"]
