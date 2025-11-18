"""Pure utility functions for consolidate command planning."""

from dataclasses import dataclass
from pathlib import Path

from erk.core.gitops import WorktreeInfo


@dataclass(frozen=True)
class ConsolidationPlan:
    """Plan for consolidating stack branches into target worktree."""

    stack_to_consolidate: list[str]
    worktrees_to_remove: list[WorktreeInfo]
    target_worktree_path: Path
    source_worktree_path: Path | None


def calculate_stack_range(
    stack_branches: list[str],
    end_branch: str | None,
) -> list[str]:
    """Calculate which branches in the stack should be consolidated.

    Args:
        stack_branches: Full list of branches in stack (trunk to leaf)
        end_branch: Branch to consolidate up to (inclusive), or None for full stack

    Returns:
        List of branch names to consolidate
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
    """Create a plan for consolidating stack branches.

    Args:
        all_worktrees: All worktrees in the repository
        stack_branches: Full list of branches in stack (trunk to leaf)
        end_branch: Branch to consolidate up to (inclusive), or None for full stack
        target_worktree_path: Path to worktree that will contain consolidated branches
        source_worktree_path: Original worktree path (if creating new target), or None

    Returns:
        ConsolidationPlan with branches and worktrees to remove
    """
    # Calculate which branches should be consolidated
    stack_to_consolidate = calculate_stack_range(stack_branches, end_branch)

    # Find worktrees to remove:
    # - Worktrees containing branches in stack_to_consolidate
    # - Skip root worktree (never removed)
    # - Skip target worktree (consolidation destination)
    worktrees_to_remove: list[WorktreeInfo] = []

    for wt in all_worktrees:
        # Skip if branch not in consolidation range
        if wt.branch not in stack_to_consolidate:
            continue

        # Skip root worktree
        if wt.is_root:
            continue

        # Skip target worktree
        if wt.path.resolve() == target_worktree_path.resolve():
            continue

        worktrees_to_remove.append(wt)

    return ConsolidationPlan(
        stack_to_consolidate=stack_to_consolidate,
        worktrees_to_remove=worktrees_to_remove,
        target_worktree_path=target_worktree_path,
        source_worktree_path=source_worktree_path,
    )
