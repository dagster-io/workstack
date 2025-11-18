"""Tests for ForestOps implementations."""

from pathlib import Path

from erk.core.forest_ops import FakeForestOps, RealForestOps
from erk.core.forest_types import Forest, ForestMetadata, RerootState


def test_fake_forest_ops_load_empty() -> None:
    """Test loading from empty FakeForestOps."""
    ops = FakeForestOps()
    metadata = ops.load_forests()

    assert metadata.forests == {}


def test_fake_forest_ops_save_and_load() -> None:
    """Test saving and loading forests in memory."""
    ops = FakeForestOps()

    forest = Forest(
        name="my-forest",
        worktrees=["wt1", "wt2"],
        created_at="2025-01-01T00:00:00Z",
        root_branch="main",
    )
    metadata = ForestMetadata(forests={"my-forest": forest})

    ops.save_forests(metadata)
    loaded = ops.load_forests()

    assert len(loaded.forests) == 1
    assert "my-forest" in loaded.forests
    assert loaded.forests["my-forest"].worktrees == ["wt1", "wt2"]


def test_fake_forest_ops_get_forest_for_worktree() -> None:
    """Test finding forest by worktree."""
    ops = FakeForestOps()

    forest1 = Forest(
        name="forest1",
        worktrees=["wt1", "wt2"],
        created_at="2025-01-01T00:00:00Z",
        root_branch="main",
    )
    forest2 = Forest(
        name="forest2",
        worktrees=["wt3"],
        created_at="2025-01-01T00:00:00Z",
        root_branch="main",
    )

    metadata = ForestMetadata(forests={"forest1": forest1, "forest2": forest2})
    ops.save_forests(metadata)

    found = ops.get_forest_for_worktree("wt2")
    assert found is not None
    assert found.name == "forest1"

    not_found = ops.get_forest_for_worktree("wt99")
    assert not_found is None


def test_fake_forest_ops_reroot_state() -> None:
    """Test reroot state persistence in memory."""
    ops = FakeForestOps()

    # Initially no state
    assert ops.load_reroot_state() is None

    # Save state
    state = RerootState(
        forest="my-forest",
        current_branch="feat-1",
        parent_branch="main",
        parent_sha="abc123",
        remaining_branches=["feat-2", "feat-3"],
        paused_on_conflicts=True,
        started_at="2025-01-01T00:00:00Z",
    )
    ops.save_reroot_state(state)

    # Load state
    loaded = ops.load_reroot_state()
    assert loaded is not None
    assert loaded.forest == "my-forest"
    assert loaded.current_branch == "feat-1"
    assert loaded.remaining_branches == ["feat-2", "feat-3"]

    # Clear state
    ops.clear_reroot_state()
    assert ops.load_reroot_state() is None


def test_real_forest_ops_load_empty(tmp_path: Path) -> None:
    """Test loading from nonexistent file."""
    ops = RealForestOps(tmp_path)
    metadata = ops.load_forests()

    assert metadata.forests == {}


def test_real_forest_ops_save_and_load(tmp_path: Path) -> None:
    """Test saving and loading forests from TOML."""
    ops = RealForestOps(tmp_path)

    forest = Forest(
        name="my-forest",
        worktrees=["wt1", "wt2"],
        created_at="2025-01-01T00:00:00Z",
        root_branch="main",
    )
    metadata = ForestMetadata(forests={"my-forest": forest})

    ops.save_forests(metadata)

    # Verify file exists
    assert (tmp_path / "forests.toml").exists()

    # Load back
    loaded = ops.load_forests()
    assert len(loaded.forests) == 1
    assert "my-forest" in loaded.forests
    assert loaded.forests["my-forest"].worktrees == ["wt1", "wt2"]
    assert loaded.forests["my-forest"].root_branch == "main"


def test_real_forest_ops_multiple_forests(tmp_path: Path) -> None:
    """Test saving and loading multiple forests."""
    ops = RealForestOps(tmp_path)

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
                worktrees=["wt2", "wt3"],
                created_at="2025-01-02T00:00:00Z",
                root_branch="develop",
            ),
        }
    )

    ops.save_forests(metadata)
    loaded = ops.load_forests()

    assert len(loaded.forests) == 2
    assert loaded.forests["forest1"].worktrees == ["wt1"]
    assert loaded.forests["forest2"].worktrees == ["wt2", "wt3"]


def test_real_forest_ops_get_forest_for_worktree(tmp_path: Path) -> None:
    """Test finding forest by worktree."""
    ops = RealForestOps(tmp_path)

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
    ops.save_forests(metadata)

    found = ops.get_forest_for_worktree("wt2")
    assert found is not None
    assert found.name == "forest1"


def test_real_forest_ops_reroot_state(tmp_path: Path) -> None:
    """Test reroot state persistence to JSON."""
    ops = RealForestOps(tmp_path)

    # Initially no state
    assert ops.load_reroot_state() is None

    # Save state
    state = RerootState(
        forest="my-forest",
        current_branch="feat-1",
        parent_branch="main",
        parent_sha="abc123def456",
        remaining_branches=["feat-2", "feat-3"],
        paused_on_conflicts=True,
        started_at="2025-01-01T00:00:00Z",
    )
    ops.save_reroot_state(state)

    # Verify file exists
    assert (tmp_path / "reroot-state.json").exists()

    # Load state
    loaded = ops.load_reroot_state()
    assert loaded is not None
    assert loaded.forest == "my-forest"
    assert loaded.current_branch == "feat-1"
    assert loaded.parent_branch == "main"
    assert loaded.parent_sha == "abc123def456"
    assert loaded.remaining_branches == ["feat-2", "feat-3"]
    assert loaded.paused_on_conflicts is True

    # Clear state
    ops.clear_reroot_state()
    assert not (tmp_path / "reroot-state.json").exists()
    assert ops.load_reroot_state() is None


def test_real_forest_ops_creates_parent_directory(tmp_path: Path) -> None:
    """Test that save operations create parent directory if needed."""
    nested_path = tmp_path / "nested" / "deep"
    ops = RealForestOps(nested_path)

    # Parent directory doesn't exist yet
    assert not nested_path.exists()

    # Save should create it
    metadata = ForestMetadata(
        forests={
            "test": Forest(
                name="test",
                worktrees=["wt1"],
                created_at="2025-01-01T00:00:00Z",
                root_branch="main",
            ),
        }
    )
    ops.save_forests(metadata)

    assert nested_path.exists()
    assert (nested_path / "forests.toml").exists()


def test_real_forest_ops_empty_forests_saves_correctly(tmp_path: Path) -> None:
    """Test saving empty forest metadata."""
    ops = RealForestOps(tmp_path)

    metadata = ForestMetadata(forests={})
    ops.save_forests(metadata)

    loaded = ops.load_forests()
    assert loaded.forests == {}
