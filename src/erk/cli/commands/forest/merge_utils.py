"""Merge planning utilities for forest operations."""

from dataclasses import dataclass
from pathlib import Path

from erk.core.forest_types import Forest
from erk.core.gitops import GitOps


@dataclass(frozen=True)
class ForestMergePlan:
    """Plan for merging forest into single worktree."""

    forest_name: str
    target_worktree: str  # Worktree to keep
    worktrees_to_remove: list[str]  # Worktrees to delete
    branches_in_forest: list[str]  # All branches in forest


def identify_removable_worktrees(forest: Forest, target_worktree: str) -> list[str]:
    """Return worktrees to remove (all except target).

    Args:
        forest: Forest to merge
        target_worktree: Worktree to keep

    Returns:
        List of worktree names to remove
    """
    return [wt for wt in forest.worktrees if wt != target_worktree]


def create_forest_merge_plan(
    forest: Forest, target_worktree: str | None, current_worktree: str | None
) -> ForestMergePlan:
    """Create merge plan for forest consolidation.

    Args:
        forest: Forest to merge
        target_worktree: Provided target worktree or None
        current_worktree: Current worktree name or None

    Returns:
        Merge plan

    Raises:
        ValueError: If target is not in forest
    """
    # Determine target
    if target_worktree is not None:
        final_target = target_worktree
    elif current_worktree is not None and current_worktree in forest.worktrees:
        final_target = current_worktree
    elif forest.worktrees:
        final_target = forest.worktrees[0]
    else:
        raise ValueError("Forest has no worktrees")

    # Validate target is in forest
    if final_target not in forest.worktrees:
        raise ValueError(f"Target worktree '{final_target}' not in forest '{forest.name}'")

    # Identify removable worktrees
    removable = identify_removable_worktrees(forest, final_target)

    return ForestMergePlan(
        forest_name=forest.name,
        target_worktree=final_target,
        worktrees_to_remove=removable,
        branches_in_forest=forest.worktrees.copy(),
    )


def check_uncommitted_changes(
    worktrees_to_check: list[str], git_ops: GitOps, worktrees_dir: Path
) -> list[str]:
    """Return list of worktrees with uncommitted changes.

    Args:
        worktrees_to_check: Worktree names to check
        git_ops: GitOps interface
        worktrees_dir: Directory containing worktrees

    Returns:
        List of worktree names with uncommitted changes
    """
    with_changes = []

    for wt_name in worktrees_to_check:
        wt_path = worktrees_dir / wt_name

        if not git_ops.path_exists(wt_path):
            continue

        if git_ops.has_uncommitted_changes(wt_path):
            with_changes.append(wt_name)

    return with_changes
