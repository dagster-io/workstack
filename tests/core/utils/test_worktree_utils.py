"""Unit tests for worktree utility functions."""

from pathlib import Path

from workstack.core.gitops import WorktreeInfo
from workstack.core.worktree_utils import (
    MoveOperationType,
    determine_move_operation,
    filter_non_trunk_branches,
    find_current_worktree,
    find_worktree_containing_path,
    find_worktree_with_branch,
    get_worktree_branch,
    is_root_worktree,
)


class TestFindWorktreeContainingPath:
    """Tests for find_worktree_containing_path function."""

    def test_finds_exact_match(self) -> None:
        """Test finding exact worktree path match."""
        worktrees = [
            WorktreeInfo(Path("/repo"), "main", True),
            WorktreeInfo(Path("/repo/workstacks/feat"), "feat", False),
        ]
        target_path = Path("/repo/workstacks/feat")

        result = find_worktree_containing_path(worktrees, target_path)

        assert result == Path("/repo/workstacks/feat")

    def test_finds_parent_worktree(self) -> None:
        """Test finding worktree when target is a subdirectory."""
        worktrees = [
            WorktreeInfo(Path("/repo"), "main", True),
            WorktreeInfo(Path("/repo/workstacks/feat"), "feat", False),
        ]
        target_path = Path("/repo/workstacks/feat/src/module")

        result = find_worktree_containing_path(worktrees, target_path)

        assert result == Path("/repo/workstacks/feat")

    def test_returns_most_specific_match(self) -> None:
        """Test returns deepest match when worktrees are nested."""
        worktrees = [
            WorktreeInfo(Path("/repo"), "main", True),
            WorktreeInfo(Path("/repo/workstacks"), "base", False),
            WorktreeInfo(Path("/repo/workstacks/feat"), "feat", False),
        ]
        target_path = Path("/repo/workstacks/feat/src")

        result = find_worktree_containing_path(worktrees, target_path)

        # Should return the most specific (deepest) match
        assert result == Path("/repo/workstacks/feat")

    def test_returns_none_when_not_found(self) -> None:
        """Test returns None when path is not in any worktree."""
        worktrees = [
            WorktreeInfo(Path("/repo"), "main", True),
            WorktreeInfo(Path("/repo/workstacks/feat"), "feat", False),
        ]
        target_path = Path("/other/path")

        result = find_worktree_containing_path(worktrees, target_path)

        assert result is None

    def test_handles_empty_worktree_list(self) -> None:
        """Test handles empty worktree list gracefully."""
        worktrees: list[WorktreeInfo] = []
        target_path = Path("/repo/src")

        result = find_worktree_containing_path(worktrees, target_path)

        assert result is None


class TestFindCurrentWorktree:
    """Tests for find_current_worktree function."""

    def test_finds_current_worktree(self) -> None:
        """Test finding the WorktreeInfo for current directory."""
        worktrees = [
            WorktreeInfo(Path("/repo"), "main", True),
            WorktreeInfo(Path("/repo/workstacks/feat"), "feat", False),
        ]
        current_dir = Path("/repo/workstacks/feat/src")

        result = find_current_worktree(worktrees, current_dir)

        assert result is not None
        assert result.path == Path("/repo/workstacks/feat")
        assert result.branch == "feat"
        assert result.is_root is False

    def test_returns_none_when_not_in_worktree(self) -> None:
        """Test returns None when current directory is not in any worktree."""
        worktrees = [
            WorktreeInfo(Path("/repo"), "main", True),
        ]
        current_dir = Path("/other/path")

        result = find_current_worktree(worktrees, current_dir)

        assert result is None

    def test_returns_root_worktree_info(self) -> None:
        """Test correctly returns root worktree info."""
        worktrees = [
            WorktreeInfo(Path("/repo"), "main", True),
            WorktreeInfo(Path("/repo/workstacks/feat"), "feat", False),
        ]
        current_dir = Path("/repo/src")

        result = find_current_worktree(worktrees, current_dir)

        assert result is not None
        assert result.path == Path("/repo")
        assert result.branch == "main"
        assert result.is_root is True


class TestIsRootWorktree:
    """Tests for is_root_worktree function."""

    def test_returns_true_for_root_worktree(self) -> None:
        """Test identifies root worktree correctly."""
        worktree_path = Path("/repo")
        repo_root = Path("/repo")

        result = is_root_worktree(worktree_path, repo_root)

        assert result is True

    def test_returns_false_for_non_root_worktree(self) -> None:
        """Test identifies non-root worktree correctly."""
        worktree_path = Path("/repo/workstacks/feat")
        repo_root = Path("/repo")

        result = is_root_worktree(worktree_path, repo_root)

        assert result is False

    def test_handles_path_normalization(self) -> None:
        """Test handles different path representations correctly."""
        # Even with trailing slashes or relative paths, should resolve correctly
        worktree_path = Path("/repo/.")
        repo_root = Path("/repo")

        result = is_root_worktree(worktree_path, repo_root)

        assert result is True


class TestGetWorktreeBranch:
    """Tests for get_worktree_branch function."""

    def test_returns_branch_for_worktree(self) -> None:
        """Test returns branch name for a given worktree path."""
        worktrees = [
            WorktreeInfo(Path("/repo"), "main", True),
            WorktreeInfo(Path("/repo/workstacks/feat"), "feature-x", False),
        ]
        wt_path = Path("/repo/workstacks/feat")

        result = get_worktree_branch(worktrees, wt_path)

        assert result == "feature-x"

    def test_returns_none_for_unknown_worktree(self) -> None:
        """Test returns None when worktree path is not found."""
        worktrees = [
            WorktreeInfo(Path("/repo"), "main", True),
        ]
        wt_path = Path("/repo/workstacks/unknown")

        result = get_worktree_branch(worktrees, wt_path)

        assert result is None

    def test_returns_none_for_detached_head(self) -> None:
        """Test returns None when worktree is in detached HEAD state."""
        worktrees = [
            WorktreeInfo(Path("/repo"), "main", True),
            WorktreeInfo(Path("/repo/workstacks/detached"), None, False),
        ]
        wt_path = Path("/repo/workstacks/detached")

        result = get_worktree_branch(worktrees, wt_path)

        assert result is None

    def test_handles_path_normalization(self) -> None:
        """Test handles different path representations correctly."""
        worktrees = [
            WorktreeInfo(Path("/repo/workstacks/feat"), "feature-x", False),
        ]
        wt_path = Path("/repo/workstacks/feat/.")  # With trailing dot

        result = get_worktree_branch(worktrees, wt_path)

        assert result == "feature-x"


class TestFindWorktreeWithBranch:
    """Tests for find_worktree_with_branch function."""

    def test_finds_worktree_with_branch(self) -> None:
        """Test finds worktree path for a given branch."""
        worktrees = [
            WorktreeInfo(Path("/repo"), "main", True),
            WorktreeInfo(Path("/repo/workstacks/feat"), "feature-x", False),
        ]

        result = find_worktree_with_branch(worktrees, "feature-x")

        assert result == Path("/repo/workstacks/feat")

    def test_returns_none_when_branch_not_found(self) -> None:
        """Test returns None when branch is not in any worktree."""
        worktrees = [
            WorktreeInfo(Path("/repo"), "main", True),
            WorktreeInfo(Path("/repo/workstacks/feat"), "feature-x", False),
        ]

        result = find_worktree_with_branch(worktrees, "unknown-branch")

        assert result is None

    def test_finds_root_worktree_branch(self) -> None:
        """Test finds root worktree by branch name."""
        worktrees = [
            WorktreeInfo(Path("/repo"), "main", True),
            WorktreeInfo(Path("/repo/workstacks/feat"), "feature-x", False),
        ]

        result = find_worktree_with_branch(worktrees, "main")

        assert result == Path("/repo")

    def test_handles_empty_worktree_list(self) -> None:
        """Test handles empty worktree list gracefully."""
        worktrees: list[WorktreeInfo] = []

        result = find_worktree_with_branch(worktrees, "any-branch")

        assert result is None


class TestFilterNonTrunkBranches:
    """Tests for filter_non_trunk_branches function."""

    def test_filters_out_trunk_branches(self) -> None:
        """Test filters out trunk branches from stack."""

        # Mock BranchInfo-like objects
        class BranchInfo:
            def __init__(self, is_trunk: bool):
                self.is_trunk = is_trunk

        all_branches = {
            "main": BranchInfo(is_trunk=True),
            "feat-1": BranchInfo(is_trunk=False),
            "feat-2": BranchInfo(is_trunk=False),
            "master": BranchInfo(is_trunk=True),
        }
        stack = ["main", "feat-1", "feat-2"]

        result = filter_non_trunk_branches(all_branches, stack)

        assert result == ["feat-1", "feat-2"]

    def test_returns_empty_when_all_trunk(self) -> None:
        """Test returns empty list when all branches are trunk."""

        class BranchInfo:
            def __init__(self, is_trunk: bool):
                self.is_trunk = is_trunk

        all_branches = {
            "main": BranchInfo(is_trunk=True),
            "master": BranchInfo(is_trunk=True),
        }
        stack = ["main", "master"]

        result = filter_non_trunk_branches(all_branches, stack)

        assert result == []

    def test_handles_missing_branches(self) -> None:
        """Test handles branches in stack that are not in all_branches."""

        class BranchInfo:
            def __init__(self, is_trunk: bool):
                self.is_trunk = is_trunk

        all_branches = {
            "main": BranchInfo(is_trunk=True),
            "feat-1": BranchInfo(is_trunk=False),
        }
        stack = ["main", "feat-1", "missing-branch"]

        result = filter_non_trunk_branches(all_branches, stack)

        # Should only include branches that exist and are not trunk
        assert result == ["feat-1"]

    def test_preserves_order(self) -> None:
        """Test preserves order of branches in stack."""

        class BranchInfo:
            def __init__(self, is_trunk: bool):
                self.is_trunk = is_trunk

        all_branches = {
            "main": BranchInfo(is_trunk=True),
            "feat-1": BranchInfo(is_trunk=False),
            "feat-2": BranchInfo(is_trunk=False),
            "feat-3": BranchInfo(is_trunk=False),
        }
        stack = ["feat-3", "feat-1", "feat-2", "main"]

        result = filter_non_trunk_branches(all_branches, stack)

        assert result == ["feat-3", "feat-1", "feat-2"]

    def test_handles_empty_stack(self) -> None:
        """Test handles empty stack gracefully."""

        class BranchInfo:
            def __init__(self, is_trunk: bool):
                self.is_trunk = is_trunk

        all_branches = {
            "main": BranchInfo(is_trunk=True),
        }
        stack: list[str] = []

        result = filter_non_trunk_branches(all_branches, stack)

        assert result == []


class TestDetermineMoveOperation:
    """Tests for determine_move_operation function."""

    def test_create_operation_when_target_doesnt_exist(self) -> None:
        """Test CREATE operation when target worktree doesn't exist."""
        worktrees = [
            WorktreeInfo(Path("/repo/source"), "feat-1", False),
        ]
        source = Path("/repo/source")
        target = Path("/repo/new")

        operation = determine_move_operation(worktrees, source, target)

        assert operation.operation_type == MoveOperationType.CREATE
        assert operation.source_path == source
        assert operation.target_path == target
        assert operation.source_branch == "feat-1"
        assert operation.target_branch is None

    def test_move_operation_when_target_is_detached(self) -> None:
        """Test MOVE operation when target exists but is detached HEAD."""
        worktrees = [
            WorktreeInfo(Path("/repo/source"), "feat-1", False),
            WorktreeInfo(Path("/repo/target"), None, False),  # Detached
        ]
        source = Path("/repo/source")
        target = Path("/repo/target")

        operation = determine_move_operation(worktrees, source, target)

        assert operation.operation_type == MoveOperationType.MOVE
        assert operation.source_branch == "feat-1"
        assert operation.target_branch is None

    def test_swap_operation_when_both_have_branches(self) -> None:
        """Test SWAP operation when both source and target have branches."""
        worktrees = [
            WorktreeInfo(Path("/repo/source"), "feat-1", False),
            WorktreeInfo(Path("/repo/target"), "feat-2", False),
        ]
        source = Path("/repo/source")
        target = Path("/repo/target")

        operation = determine_move_operation(worktrees, source, target)

        assert operation.operation_type == MoveOperationType.SWAP
        assert operation.source_branch == "feat-1"
        assert operation.target_branch == "feat-2"

    def test_source_in_detached_head_state(self) -> None:
        """Test when source worktree is in detached HEAD."""
        worktrees = [
            WorktreeInfo(Path("/repo/source"), None, False),  # Detached
            WorktreeInfo(Path("/repo/target"), "feat-1", False),
        ]
        source = Path("/repo/source")
        target = Path("/repo/target")

        operation = determine_move_operation(worktrees, source, target)

        assert operation.source_branch is None
        assert operation.target_branch == "feat-1"
        # Would still be SWAP since target has branch
        assert operation.operation_type == MoveOperationType.SWAP

    def test_move_from_root_worktree(self) -> None:
        """Test moving from root worktree to new location."""
        worktrees = [
            WorktreeInfo(Path("/repo"), "main", True),
        ]
        source = Path("/repo")
        target = Path("/repo/new")

        operation = determine_move_operation(worktrees, source, target)

        assert operation.operation_type == MoveOperationType.CREATE
        assert operation.source_branch == "main"
        assert operation.target_branch is None

    def test_immutable_move_operation(self) -> None:
        """Test that MoveOperation is frozen (immutable)."""
        worktrees = [
            WorktreeInfo(Path("/repo/source"), "feat-1", False),
        ]

        operation = determine_move_operation(worktrees, Path("/repo/source"), Path("/repo/new"))

        # Verify frozen dataclass
        import pytest

        with pytest.raises(AttributeError):
            operation.operation_type = MoveOperationType.SWAP  # type: ignore[misc]

    def test_multiple_worktrees_only_relevant_ones_checked(self) -> None:
        """Test that only source and target worktrees matter."""
        worktrees = [
            WorktreeInfo(Path("/repo"), "main", True),
            WorktreeInfo(Path("/repo/other1"), "feat-1", False),
            WorktreeInfo(Path("/repo/source"), "feat-2", False),
            WorktreeInfo(Path("/repo/other2"), "feat-3", False),
            WorktreeInfo(Path("/repo/target"), "feat-4", False),
        ]
        source = Path("/repo/source")
        target = Path("/repo/target")

        operation = determine_move_operation(worktrees, source, target)

        assert operation.operation_type == MoveOperationType.SWAP
        assert operation.source_branch == "feat-2"
        assert operation.target_branch == "feat-4"

    def test_resolved_paths_for_comparison(self) -> None:
        """Test that paths are resolved for comparison."""
        worktrees = [
            WorktreeInfo(Path("/repo/source"), "feat-1", False),
            WorktreeInfo(Path("/repo/target"), "feat-2", False),
        ]
        # Use relative path that resolves to same location
        source = Path("/repo/source")
        target = Path("/repo/../repo/target")  # Same as /repo/target

        operation = determine_move_operation(worktrees, source, target)

        assert operation.operation_type == MoveOperationType.SWAP
