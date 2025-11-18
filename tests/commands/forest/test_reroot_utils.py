"""Unit tests for forest reroot utilities."""

from pathlib import Path

import pytest

from erk.cli.commands.forest.reroot_utils import (
    create_reroot_marker,
    create_reroot_plan,
    detect_conflict_markers,
    format_conflict_commit_message,
    format_progress_message,
    format_resolved_commit_message,
)
from erk.core.forest_types import Forest
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.test_utils import sentinel_path


def test_create_reroot_plan() -> None:
    """Test creating reroot plan with branch ordering."""
    forest = Forest(
        name="my-forest",
        worktrees=["feat-1", "feat-2"],
        created_at="2025-01-01T00:00:00Z",
        root_branch="main",
    )

    graphite_ops = FakeGraphiteOps(
        stacks={
            "feat-1": ["main", "feat-1", "feat-2"],
        }
    )
    git_ops = FakeGitOps()

    plan = create_reroot_plan(forest, graphite_ops, git_ops, "main", sentinel_path())

    assert plan.forest_name == "my-forest"
    assert plan.target_base == "main"
    assert plan.total_branches == 2
    assert len(plan.branches_in_order) == 2
    assert plan.branches_in_order[0] == ("feat-1", "main")
    assert plan.branches_in_order[1] == ("feat-2", "feat-1")


def test_create_reroot_plan_empty_forest() -> None:
    """Test creating plan for empty forest."""
    forest = Forest(
        name="my-forest",
        worktrees=[],
        created_at="2025-01-01T00:00:00Z",
        root_branch="main",
    )

    graphite_ops = FakeGraphiteOps()
    git_ops = FakeGitOps()

    with pytest.raises(ValueError, match="has no worktrees"):
        create_reroot_plan(forest, graphite_ops, git_ops, "main", sentinel_path())


def test_format_conflict_commit_message() -> None:
    """Test formatting conflict commit message."""
    result = format_conflict_commit_message("main", "abc123def456")

    assert result == "[CONFLICT] Rebase conflicts from main (abc123d)"


def test_format_resolved_commit_message() -> None:
    """Test formatting resolved commit message."""
    result = format_resolved_commit_message("main", "abc123def456")

    assert result == "[RESOLVED] Fix rebase conflicts from main (abc123d)"


def test_detect_conflict_markers_with_conflicts(tmp_path: Path) -> None:
    """Test detecting conflict markers in file."""
    file_path = tmp_path / "test.txt"
    file_path.write_text(
        "line 1\n<<<<<<< HEAD\nmy changes\n=======\ntheir changes\n>>>>>>> branch\n",
        encoding="utf-8",
    )

    result = detect_conflict_markers(file_path)

    assert result is True


def test_detect_conflict_markers_clean_file(tmp_path: Path) -> None:
    """Test detecting no conflict markers in clean file."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("clean content\nno conflicts here\n", encoding="utf-8")

    result = detect_conflict_markers(file_path)

    assert result is False


def test_detect_conflict_markers_nonexistent() -> None:
    """Test detecting conflict markers in nonexistent file."""
    result = detect_conflict_markers(Path("/nonexistent/file.txt"))

    assert result is False


def test_create_reroot_marker() -> None:
    """Test creating reroot marker."""
    marker = create_reroot_marker("my-forest", "feat-1")

    assert marker.forest == "my-forest"
    assert marker.current_branch == "feat-1"
    assert "T" in marker.started_at  # ISO 8601 format


def test_format_progress_message() -> None:
    """Test formatting progress message."""
    result = format_progress_message(2, 5, "feat-branch")

    assert result == "Processing branch 2/5: feat-branch"
