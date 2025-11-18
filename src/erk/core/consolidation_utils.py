"""Utility functions for worktree consolidation planning."""

from dataclasses import dataclass
from pathlib import Path

from erk.core.gitops import WorktreeInfo


@dataclass(frozen=True)
class ConsolidationPlan:
    """Plan for consolidating worktrees containing stack branches."""

    stack_to_consolidate: list[str]
    worktrees_to_remove: list[WorktreeInfo]


def calculate_stack_range(
    stack_branches: list[str],
    end_branch: str | None,
) -> list[str]:
    """Calculate the range of branches to consolidate.

    Args:
        stack_branches: Full stack from trunk to leaf (ordered)
        end_branch: Optional branch to end consolidation at (None = full stack)

    Returns:
        List of branches to consolidate (trunk to end_branch, or full stack if None)
    """
    if end_branch is None:
        return stack_branches

    if end_branch not in stack_branches:
        return stack_branches

    # Return branches from trunk up to and including end_branch
    end_index = stack_branches.index(end_branch)
    return stack_branches[: end_index + 1]


def create_consolidation_plan(
    all_worktrees: list[WorktreeInfo],
    stack_branches: list[str],
    end_branch: str | None,
    target_worktree_path: Path,
    source_worktree_path: Path | None,
) -> ConsolidationPlan:
    """Create a consolidation plan identifying worktrees to remove.

    Args:
        all_worktrees: All worktrees in the repository
        stack_branches: Full stack branches (trunk to leaf)
        end_branch: Optional branch to end consolidation at (None = full stack)
        target_worktree_path: Path of the target worktree (where branches will be consolidated)
        source_worktree_path: Path of source worktree if creating new target (to be removed)

    Returns:
        ConsolidationPlan with stack range and worktrees to remove
    """
    stack_to_consolidate = calculate_stack_range(stack_branches, end_branch)

    worktrees_to_remove: list[WorktreeInfo] = []
    for wt in all_worktrees:
        # Skip worktrees not in consolidation range
        if wt.branch not in stack_to_consolidate:
            continue

        # Skip root worktree (never remove)
        if wt.is_root:
            continue

        # Skip target worktree (consolidation destination)
        if wt.path.resolve() == target_worktree_path.resolve():
            continue

        # Skip source worktree if creating new target (handled separately)
        if source_worktree_path is not None and wt.path.resolve() == source_worktree_path.resolve():
            continue

        worktrees_to_remove.append(wt)

    return ConsolidationPlan(
        stack_to_consolidate=stack_to_consolidate,
        worktrees_to_remove=worktrees_to_remove,
    )
