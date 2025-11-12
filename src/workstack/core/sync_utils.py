"""Pure business logic for sync command operations.

This module contains testable functions for identifying deletable worktrees
based on their PR state, without I/O dependencies.
"""

from dataclasses import dataclass
from pathlib import Path

from workstack.core.gitops import WorktreeInfo


@dataclass(frozen=True)
class DeletableWorktree:
    """Information about a worktree eligible for deletion."""

    name: str
    branch: str
    pr_state: str  # "MERGED" or "CLOSED"
    pr_number: int


@dataclass(frozen=True)
class PRStatus:
    """PR status information for a branch."""

    branch: str
    state: str  # "MERGED", "CLOSED", "OPEN", etc.
    pr_number: int | None
    title: str | None


def identify_deletable_worktrees(
    worktrees: list[WorktreeInfo],
    pr_statuses: dict[str, PRStatus],
    repo_root: Path,
    workstacks_dir: Path,
) -> list[DeletableWorktree]:
    """Identify worktrees that are safe to delete based on PR state.

    A worktree is deletable if:
    - It's not the root worktree
    - It's not in detached HEAD state
    - It's managed by workstack (located in workstacks_dir)
    - Its PR is MERGED or CLOSED

    Args:
        worktrees: List of all worktrees in the repository
        pr_statuses: Map of branch name to PR status information
        repo_root: Path to the repository root
        workstacks_dir: Path to the workstacks directory containing managed worktrees

    Returns:
        List of worktrees that can be safely deleted

    Example:
        >>> worktrees = [
        ...     WorktreeInfo(Path("/repo"), "main", is_root=True),
        ...     WorktreeInfo(Path("/repo/.workstacks/feat-1"), "feat-1"),
        ... ]
        >>> pr_statuses = {
        ...     "feat-1": PRStatus("feat-1", "MERGED", 123, "Add feature")
        ... }
        >>> deletable = identify_deletable_worktrees(
        ...     worktrees, pr_statuses, Path("/repo"), Path("/repo/.workstacks")
        ... )
        >>> len(deletable)
        1
        >>> deletable[0].name
        'feat-1'
    """
    deletable: list[DeletableWorktree] = []

    for wt in worktrees:
        # Skip root worktree
        if wt.path == repo_root:
            continue

        # Skip detached HEAD
        if wt.branch is None:
            continue

        # Skip non-managed worktrees
        if wt.path.parent != workstacks_dir:
            continue

        # Check if we have PR status for this branch
        if wt.branch not in pr_statuses:
            continue

        pr_status = pr_statuses[wt.branch]

        # Only delete if PR is merged or closed AND has a PR number
        if pr_status.state in ("MERGED", "CLOSED") and pr_status.pr_number is not None:
            deletable.append(
                DeletableWorktree(
                    name=wt.path.name,
                    branch=wt.branch,
                    pr_state=pr_status.state,
                    pr_number=pr_status.pr_number,
                )
            )

    return deletable
