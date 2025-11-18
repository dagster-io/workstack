"""Split planning utilities for forest operations."""

from dataclasses import dataclass

from erk.core.forest_types import ForestMetadata
from erk.core.forest_utils import find_forest_by_worktree
from erk.core.gitops import WorktreeInfo


@dataclass(frozen=True)
class ForestSplitPlan:
    """Plan for splitting worktree into forest."""

    forest_name: str
    branches_to_split: list[str]  # Branches needing new worktrees
    worktrees_to_create: list[str]  # Worktree names to create
    current_branch: str


def identify_splittable_branches(
    stack_branches: list[str],
    current_branch: str,
    trunk_branch: str,
    existing_worktrees: list[WorktreeInfo],
    direction: str | None,
) -> list[str]:
    """Identify branches that need worktrees.

    Args:
        stack_branches: All branches in the stack (trunk to leaf order)
        current_branch: Current branch name
        trunk_branch: Trunk branch name
        existing_worktrees: List of existing worktrees
        direction: "up" (upstack), "down" (downstack), or None (all)

    Returns:
        List of branch names that need worktrees created
    """
    existing_branches = {wt.branch for wt in existing_worktrees if wt.branch}

    # Exclude trunk and current branch
    candidates = [b for b in stack_branches if b != trunk_branch and b != current_branch]

    # Filter by direction if specified
    if direction is not None:
        try:
            current_idx = stack_branches.index(current_branch)
        except ValueError:
            # Current branch not in stack, return empty
            return []

        if direction == "up":
            # Upstack = toward leaves (higher indices)
            candidates = [b for b in candidates if stack_branches.index(b) > current_idx]
        elif direction == "down":
            # Downstack = toward trunk (lower indices)
            candidates = [b for b in candidates if stack_branches.index(b) < current_idx]

    # Exclude branches with existing worktrees
    return [b for b in candidates if b not in existing_branches]


def create_forest_split_plan(
    stack_branches: list[str],
    current_branch: str,
    trunk_branch: str,
    existing_worktrees: list[WorktreeInfo],
    direction: str | None,
    forest_name: str | None,
    forest_metadata: ForestMetadata,
) -> ForestSplitPlan:
    """Create split plan with forest name and worktrees.

    Args:
        stack_branches: All branches in stack
        current_branch: Current branch name
        trunk_branch: Trunk branch name
        existing_worktrees: Existing worktrees
        direction: "up", "down", or None
        forest_name: Provided forest name or None
        forest_metadata: Current forest metadata

    Returns:
        Split plan with forest name and worktrees to create
    """
    # Identify branches to split
    branches_to_split = identify_splittable_branches(
        stack_branches, current_branch, trunk_branch, existing_worktrees, direction
    )

    # Determine forest name
    final_forest_name = detect_or_create_forest_name(current_branch, forest_metadata, forest_name)

    # Worktree names match branch names (will be sanitized later)
    worktrees_to_create = branches_to_split.copy()

    return ForestSplitPlan(
        forest_name=final_forest_name,
        branches_to_split=branches_to_split,
        worktrees_to_create=worktrees_to_create,
        current_branch=current_branch,
    )


def detect_or_create_forest_name(
    current_branch: str,
    forest_metadata: ForestMetadata,
    provided_name: str | None,
) -> str:
    """Determine forest name (auto-detect or create new).

    Args:
        current_branch: Current branch name
        forest_metadata: Current forest metadata
        provided_name: User-provided forest name or None

    Returns:
        Forest name to use
    """
    if provided_name is not None:
        return provided_name

    # Check if current branch is in a forest
    existing_forest = find_forest_by_worktree(forest_metadata, current_branch)
    if existing_forest is not None:
        return existing_forest.name

    # Use current branch name as forest name
    return current_branch
