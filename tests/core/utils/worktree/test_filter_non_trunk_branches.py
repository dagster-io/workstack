"""Tests for filter_non_trunk_branches function."""

from workstack.core.worktree_utils import filter_non_trunk_branches


def test_filters_out_trunk_branches() -> None:
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


def test_returns_empty_when_all_trunk() -> None:
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


def test_handles_missing_branches() -> None:
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


def test_preserves_order() -> None:
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


def test_handles_empty_stack() -> None:
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
