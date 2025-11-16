"""Tests for sync_utils module - pure business logic for sync operations."""

from pathlib import Path

import pytest

from erk.core.gitops import WorktreeInfo
from erk.core.sync_utils import (
    DeletableWorktree,
    PRStatus,
    identify_deletable_worktrees,
)

# Tests for identify_deletable_worktrees function


def test_identifies_merged_pr() -> None:
    """Test identification of worktree with merged PR."""
    repo_root = Path("/repo")
    workstacks_dir = Path("/repo/.workstacks")

    worktrees = [
        WorktreeInfo(repo_root, "main", is_root=True),
        WorktreeInfo(workstacks_dir / "feat-1", "feat-1"),
    ]

    pr_statuses = {
        "main": PRStatus("main", "OPEN", 100, "Main PR"),
        "feat-1": PRStatus("feat-1", "MERGED", 123, "Add feature"),
    }

    deletable = identify_deletable_worktrees(worktrees, pr_statuses, repo_root, workstacks_dir)

    assert len(deletable) == 1
    assert deletable[0].name == "feat-1"
    assert deletable[0].branch == "feat-1"
    assert deletable[0].pr_state == "MERGED"
    assert deletable[0].pr_number == 123


def test_identifies_closed_pr() -> None:
    """Test identification of worktree with closed PR."""
    repo_root = Path("/repo")
    workstacks_dir = Path("/repo/.workstacks")

    worktrees = [
        WorktreeInfo(repo_root, "main", is_root=True),
        WorktreeInfo(workstacks_dir / "feat-1", "feat-1"),
    ]

    pr_statuses = {
        "feat-1": PRStatus("feat-1", "CLOSED", 123, "Closed feature"),
    }

    deletable = identify_deletable_worktrees(worktrees, pr_statuses, repo_root, workstacks_dir)

    assert len(deletable) == 1
    assert deletable[0].pr_state == "CLOSED"


def test_skips_root_worktree() -> None:
    """Test that root worktree is never deletable."""
    repo_root = Path("/repo")
    workstacks_dir = Path("/repo/.workstacks")

    worktrees = [
        WorktreeInfo(repo_root, "main", is_root=True),
    ]

    pr_statuses = {
        "main": PRStatus("main", "MERGED", 100, "Main"),
    }

    deletable = identify_deletable_worktrees(worktrees, pr_statuses, repo_root, workstacks_dir)

    assert len(deletable) == 0


def test_skips_detached_head() -> None:
    """Test that worktrees in detached HEAD state are not deletable."""
    repo_root = Path("/repo")
    workstacks_dir = Path("/repo/.workstacks")

    worktrees = [
        WorktreeInfo(repo_root, "main", is_root=True),
        WorktreeInfo(workstacks_dir / "detached", None),  # Detached HEAD
    ]

    pr_statuses = {}

    deletable = identify_deletable_worktrees(worktrees, pr_statuses, repo_root, workstacks_dir)

    assert len(deletable) == 0


def test_skips_non_managed_worktrees() -> None:
    """Test that worktrees outside workstacks_dir are not deletable."""
    repo_root = Path("/repo")
    workstacks_dir = Path("/repo/.workstacks")

    worktrees = [
        WorktreeInfo(repo_root, "main", is_root=True),
        WorktreeInfo(Path("/other/location/feat-1"), "feat-1"),  # Not in workstacks_dir
    ]

    pr_statuses = {
        "feat-1": PRStatus("feat-1", "MERGED", 123, "Feature"),
    }

    deletable = identify_deletable_worktrees(worktrees, pr_statuses, repo_root, workstacks_dir)

    assert len(deletable) == 0


def test_skips_open_prs() -> None:
    """Test that worktrees with open PRs are not deletable."""
    repo_root = Path("/repo")
    workstacks_dir = Path("/repo/.workstacks")

    worktrees = [
        WorktreeInfo(repo_root, "main", is_root=True),
        WorktreeInfo(workstacks_dir / "feat-1", "feat-1"),
    ]

    pr_statuses = {
        "feat-1": PRStatus("feat-1", "OPEN", 123, "Work in progress"),
    }

    deletable = identify_deletable_worktrees(worktrees, pr_statuses, repo_root, workstacks_dir)

    assert len(deletable) == 0


def test_skips_branches_without_pr_status() -> None:
    """Test that worktrees without PR status are not deletable."""
    repo_root = Path("/repo")
    workstacks_dir = Path("/repo/.workstacks")

    worktrees = [
        WorktreeInfo(repo_root, "main", is_root=True),
        WorktreeInfo(workstacks_dir / "feat-1", "feat-1"),
    ]

    pr_statuses = {}  # No PR status for feat-1

    deletable = identify_deletable_worktrees(worktrees, pr_statuses, repo_root, workstacks_dir)

    assert len(deletable) == 0


def test_skips_merged_pr_without_number() -> None:
    """Test that merged PRs without a PR number are not deletable."""
    repo_root = Path("/repo")
    workstacks_dir = Path("/repo/.workstacks")

    worktrees = [
        WorktreeInfo(repo_root, "main", is_root=True),
        WorktreeInfo(workstacks_dir / "feat-1", "feat-1"),
    ]

    pr_statuses = {
        "feat-1": PRStatus("feat-1", "MERGED", None, "Merged without PR"),
    }

    deletable = identify_deletable_worktrees(worktrees, pr_statuses, repo_root, workstacks_dir)

    assert len(deletable) == 0


def test_identifies_multiple_deletable_worktrees() -> None:
    """Test identification of multiple deletable worktrees."""
    repo_root = Path("/repo")
    workstacks_dir = Path("/repo/.workstacks")

    worktrees = [
        WorktreeInfo(repo_root, "main", is_root=True),
        WorktreeInfo(workstacks_dir / "feat-1", "feat-1"),
        WorktreeInfo(workstacks_dir / "feat-2", "feat-2"),
        WorktreeInfo(workstacks_dir / "feat-3", "feat-3"),
    ]

    pr_statuses = {
        "feat-1": PRStatus("feat-1", "MERGED", 123, "Feature 1"),
        "feat-2": PRStatus("feat-2", "CLOSED", 124, "Feature 2"),
        "feat-3": PRStatus("feat-3", "OPEN", 125, "Feature 3"),
    }

    deletable = identify_deletable_worktrees(worktrees, pr_statuses, repo_root, workstacks_dir)

    assert len(deletable) == 2
    assert deletable[0].name == "feat-1"
    assert deletable[0].pr_state == "MERGED"
    assert deletable[1].name == "feat-2"
    assert deletable[1].pr_state == "CLOSED"


def test_mixed_scenarios() -> None:
    """Test complex scenario with multiple conditions."""
    repo_root = Path("/repo")
    workstacks_dir = Path("/repo/.workstacks")

    worktrees = [
        WorktreeInfo(repo_root, "main", is_root=True),  # Root - skip
        WorktreeInfo(workstacks_dir / "merged-wt", "merged-branch"),  # Merged - deletable
        WorktreeInfo(workstacks_dir / "open-wt", "open-branch"),  # Open - skip
        WorktreeInfo(workstacks_dir / "detached-wt", None),  # Detached - skip
        WorktreeInfo(Path("/other/location"), "external-branch"),  # External - skip
        WorktreeInfo(workstacks_dir / "closed-wt", "closed-branch"),  # Closed - deletable
        WorktreeInfo(workstacks_dir / "no-pr-wt", "no-pr-branch"),  # No PR status - skip
    ]

    pr_statuses = {
        "merged-branch": PRStatus("merged-branch", "MERGED", 100, "Merged"),
        "open-branch": PRStatus("open-branch", "OPEN", 101, "Open"),
        "external-branch": PRStatus("external-branch", "MERGED", 102, "External"),
        "closed-branch": PRStatus("closed-branch", "CLOSED", 103, "Closed"),
    }

    deletable = identify_deletable_worktrees(worktrees, pr_statuses, repo_root, workstacks_dir)

    assert len(deletable) == 2
    assert {wt.name for wt in deletable} == {"merged-wt", "closed-wt"}


def test_empty_worktrees_list() -> None:
    """Test with empty worktrees list."""
    repo_root = Path("/repo")
    workstacks_dir = Path("/repo/.workstacks")

    deletable = identify_deletable_worktrees([], {}, repo_root, workstacks_dir)

    assert len(deletable) == 0


def test_empty_pr_statuses() -> None:
    """Test with empty PR statuses dict."""
    repo_root = Path("/repo")
    workstacks_dir = Path("/repo/.workstacks")

    worktrees = [
        WorktreeInfo(repo_root, "main", is_root=True),
        WorktreeInfo(workstacks_dir / "feat-1", "feat-1"),
    ]

    deletable = identify_deletable_worktrees(worktrees, {}, repo_root, workstacks_dir)

    assert len(deletable) == 0


def test_worktree_name_extraction() -> None:
    """Test that worktree name is correctly extracted from path."""
    repo_root = Path("/repo")
    workstacks_dir = Path("/repo/.workstacks")

    worktrees = [
        WorktreeInfo(repo_root, "main", is_root=True),
        WorktreeInfo(workstacks_dir / "my-feature-branch", "feat-1"),
    ]

    pr_statuses = {
        "feat-1": PRStatus("feat-1", "MERGED", 123, "Feature"),
    }

    deletable = identify_deletable_worktrees(worktrees, pr_statuses, repo_root, workstacks_dir)

    assert len(deletable) == 1
    assert deletable[0].name == "my-feature-branch"
    assert deletable[0].branch == "feat-1"


# Tests for DeletableWorktree dataclass


class TestDeletableWorktree:
    """Tests for DeletableWorktree data class."""

    def test_frozen_dataclass(self) -> None:
        """Test that DeletableWorktree is immutable."""
        wt = DeletableWorktree(name="feat-1", branch="feature-1", pr_state="MERGED", pr_number=123)

        with pytest.raises(AttributeError):
            wt.name = "new-name"  # type: ignore[misc]

    def test_dataclass_fields(self) -> None:
        """Test DeletableWorktree has expected fields."""
        wt = DeletableWorktree(name="feat-1", branch="feature-1", pr_state="CLOSED", pr_number=456)

        assert wt.name == "feat-1"
        assert wt.branch == "feature-1"
        assert wt.pr_state == "CLOSED"
        assert wt.pr_number == 456


# Tests for PRStatus dataclass


class TestPRStatus:
    """Tests for PRStatus data class."""

    def test_frozen_dataclass(self) -> None:
        """Test that PRStatus is immutable."""
        pr = PRStatus(branch="feat-1", state="OPEN", pr_number=123, title="Feature")

        with pytest.raises(AttributeError):
            pr.state = "MERGED"  # type: ignore[misc]

    def test_dataclass_fields(self) -> None:
        """Test PRStatus has expected fields."""
        pr = PRStatus(branch="feat-1", state="MERGED", pr_number=123, title="Add feature")

        assert pr.branch == "feat-1"
        assert pr.state == "MERGED"
        assert pr.pr_number == 123
        assert pr.title == "Add feature"

    def test_optional_pr_number(self) -> None:
        """Test PRStatus with None pr_number."""
        pr = PRStatus(branch="feat-1", state="NONE", pr_number=None, title="No PR")

        assert pr.pr_number is None

    def test_optional_title(self) -> None:
        """Test PRStatus with None title."""
        pr = PRStatus(branch="feat-1", state="NONE", pr_number=None, title=None)

        assert pr.title is None
