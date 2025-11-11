"""Utility functions for worktree operations.

This module provides pure business logic functions for worktree operations,
separated from I/O and CLI concerns. These functions work with data objects
(WorktreeInfo) and enable fast unit testing.
"""

from pathlib import Path
from typing import Any

from workstack.core.gitops import WorktreeInfo


def find_worktree_containing_path(worktrees: list[WorktreeInfo], target_path: Path) -> Path | None:
    """Find which worktree contains the given path.

    Returns the most specific (deepest) match to handle nested worktrees correctly.

    Args:
        worktrees: List of WorktreeInfo objects to search
        target_path: Path to check (should be resolved)

    Returns:
        Path to the worktree that contains target_path, or None if not found

    Examples:
        >>> worktrees = [WorktreeInfo(Path("/repo"), "main", True),
        ...              WorktreeInfo(Path("/repo/workstacks/feat"), "feat", False)]
        >>> find_worktree_containing_path(worktrees, Path("/repo/workstacks/feat/src"))
        Path("/repo/workstacks/feat")  # Returns deepest match
    """
    best_match: Path | None = None
    best_match_depth = -1

    for wt in worktrees:
        wt_path = wt.path.resolve()

        # Check if target_path is within this worktree
        # is_relative_to() returns True if target_path is under wt_path
        if target_path.is_relative_to(wt_path):
            # Count path depth to find most specific match
            depth = len(wt_path.parts)
            if depth > best_match_depth:
                best_match = wt_path
                best_match_depth = depth

    return best_match


def find_current_worktree(worktrees: list[WorktreeInfo], current_dir: Path) -> WorktreeInfo | None:
    """Find the WorktreeInfo object for the worktree containing current_dir.

    Higher-level wrapper around find_worktree_containing_path that returns
    the full WorktreeInfo object instead of just the path.

    Args:
        worktrees: List of WorktreeInfo objects to search
        current_dir: Current directory path (should be resolved)

    Returns:
        WorktreeInfo object if found, None if not in any worktree

    Examples:
        >>> worktrees = [WorktreeInfo(Path("/repo"), "main", True)]
        >>> find_current_worktree(worktrees, Path("/repo/src"))
        WorktreeInfo(path=Path("/repo"), branch="main", is_root=True)
    """
    wt_path = find_worktree_containing_path(worktrees, current_dir)
    if wt_path is None:
        return None

    # Find and return the matching WorktreeInfo object
    for wt in worktrees:
        if wt.path.resolve() == wt_path:
            return wt

    return None


def is_root_worktree(worktree_path: Path, repo_root: Path) -> bool:
    """Check if a worktree path is the repository root worktree.

    Compares resolved paths to determine if the worktree is the root.

    Args:
        worktree_path: Path to the worktree to check
        repo_root: Path to the repository root

    Returns:
        True if worktree_path is the root worktree, False otherwise

    Examples:
        >>> is_root_worktree(Path("/repo"), Path("/repo"))
        True
        >>> is_root_worktree(Path("/repo/workstacks/feat"), Path("/repo"))
        False
    """
    return worktree_path.resolve() == repo_root.resolve()


def get_worktree_branch(worktrees: list[WorktreeInfo], wt_path: Path) -> str | None:
    """Get the branch checked out in a worktree.

    Returns None if worktree is not found or is in detached HEAD state.

    Args:
        worktrees: List of WorktreeInfo objects to search
        wt_path: Path to the worktree

    Returns:
        Branch name if found and checked out, None otherwise

    Examples:
        >>> worktrees = [WorktreeInfo(Path("/repo/workstacks/feat"), "feature-x", False)]
        >>> get_worktree_branch(worktrees, Path("/repo/workstacks/feat"))
        "feature-x"
        >>> get_worktree_branch(worktrees, Path("/repo/workstacks/other"))
        None
    """
    # Resolve paths for comparison to handle relative vs absolute paths
    wt_path_resolved = wt_path.resolve()
    for wt in worktrees:
        if wt.path.resolve() == wt_path_resolved:
            return wt.branch
    return None


def find_worktree_with_branch(worktrees: list[WorktreeInfo], branch: str) -> Path | None:
    """Find the worktree path containing the specified branch.

    Returns None if the branch is not found in any worktree.

    Args:
        worktrees: List of WorktreeInfo objects to search
        branch: Branch name to find

    Returns:
        Path to worktree containing the branch, or None if not found

    Examples:
        >>> worktrees = [WorktreeInfo(Path("/repo/workstacks/feat"), "feature-x", False)]
        >>> find_worktree_with_branch(worktrees, "feature-x")
        Path("/repo/workstacks/feat")
        >>> find_worktree_with_branch(worktrees, "unknown")
        None
    """
    for wt in worktrees:
        if wt.branch == branch:
            return wt.path
    return None


def filter_non_trunk_branches(all_branches: dict[str, Any], stack: list[str]) -> list[str]:
    """Filter out trunk branches from a stack.

    Args:
        all_branches: Dictionary mapping branch names to branch info (with is_trunk attribute)
        stack: List of branch names to filter

    Returns:
        List of non-trunk branches from the stack

    Examples:
        >>> branches = {"main": BranchInfo(is_trunk=True), "feat": BranchInfo(is_trunk=False)}
        >>> filter_non_trunk_branches(branches, ["main", "feat"])
        ["feat"]
    """
    return [b for b in stack if b in all_branches and not all_branches[b].is_trunk]
