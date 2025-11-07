"""Graphite integration for workstack.

Graphite (https://graphite.dev) is a stacked git workflow tool that allows developers
to manage dependent branches in linear stacks. This module provides utility functions
for working with Graphite stacks and worktrees.

For comprehensive gt mental model and command reference, see:
.agent/GT_MENTAL_MODEL.md

## What is Graphite?

Graphite organizes branches into "stacks" - linear chains of dependent branches built
on top of each other. For example:

    main (trunk)
      └─ feature/phase-1
           └─ feature/phase-2
                └─ feature/phase-3

Each branch in the stack depends on its parent, making it easy to work on multiple
related changes while keeping them in separate PRs.

## GraphiteOps Abstraction

This module uses the GraphiteOps abstraction to read Graphite cache data. Production
code should use ctx.graphite_ops methods directly instead of importing functions from
this module.

See workstack.core.graphite_ops for the abstraction interface.
"""

from pathlib import Path

from workstack.core.context import WorkstackContext
from workstack.core.gitops import WorktreeInfo


def find_worktrees_containing_branch(
    ctx: WorkstackContext,
    repo_root: Path,
    worktrees: list[WorktreeInfo],
    target_branch: str,
) -> list[WorktreeInfo]:
    """Find all worktrees that have target_branch in their Graphite stack.

    Args:
        ctx: Workstack context with git operations
        repo_root: Path to the repository root
        worktrees: List of all worktrees from list_worktrees()
        target_branch: Branch name to search for

    Returns:
        List of WorktreeInfo objects whose stacks contain target_branch.
        Empty list if no worktrees contain the branch.

    Algorithm:
        1. For each worktree:
           a. Get the worktree's checked-out branch
           b. Skip worktrees with detached HEAD (branch=None)
           c. Call ctx.graphite_ops.get_branch_stack() to get the full stack
           d. Check if target_branch is in that stack
           e. If yes, add worktree to results
        2. Return all matching worktrees

    Example:
        >>> worktrees = ctx.git_ops.list_worktrees(repo.root)
        >>> matching = find_worktrees_containing_branch(ctx, repo.root, worktrees, "feature-2")
        >>> print([wt.path for wt in matching])
        [Path("/path/to/work/feature-work")]
    """
    matching_worktrees: list[WorktreeInfo] = []

    for wt in worktrees:
        # Skip worktrees with detached HEAD
        if wt.branch is None:
            continue

        # Get the stack for this worktree's branch using GraphiteOps abstraction
        stack = ctx.graphite_ops.get_branch_stack(ctx.git_ops, repo_root, wt.branch)
        if stack is None:
            # Graphite cache doesn't exist or branch not tracked
            continue

        # Check if target_branch is in this stack
        if target_branch in stack:
            matching_worktrees.append(wt)

    return matching_worktrees


def find_worktree_for_branch(worktrees: list[WorktreeInfo], branch: str) -> Path | None:
    """Find the worktree path for a given branch.

    Args:
        worktrees: List of WorktreeInfo from ctx.git_ops.list_worktrees()
        branch: Branch name to search for

    Returns:
        Path to the worktree if branch is checked out in a worktree,
        None if no worktree exists for the branch.

    Note:
        This function expects WorktreeInfo objects with 'path' and 'branch' attributes.

    Example:
        >>> worktrees = ctx.git_ops.list_worktrees(repo.root)
        >>> wt_path = find_worktree_for_branch(worktrees, "feature-1")
        >>> print(wt_path)
        Path("/path/to/work/feature-1")
    """
    for wt in worktrees:
        if hasattr(wt, "branch") and wt.branch == branch:
            return wt.path
    return None
