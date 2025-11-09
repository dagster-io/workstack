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


def find_worktree_for_branch(
    worktrees: list[WorktreeInfo],
    branch: str,
) -> Path | None:
    """Find the worktree path for a given branch name.

    Args:
        worktrees: List of all worktrees
        branch: Branch name to search for

    Returns:
        Path to the worktree with the matching branch, or None if not found.
        Skips worktrees with detached HEAD (branch=None).

    Example:
        >>> worktrees = ctx.git_ops.list_worktrees(repo.root)
        >>> path = find_worktree_for_branch(worktrees, "feature-2")
        >>> if path:
        ...     print(f"Branch checked out in: {path}")
    """
    for wt in worktrees:
        # Skip worktrees with detached HEAD
        if wt.branch is None:
            continue

        # Check if branch matches exactly
        if wt.branch == branch:
            return wt.path

    return None


def find_worktrees_containing_branch(
    ctx: WorkstackContext,
    repo_root: Path,
    worktrees: list[WorktreeInfo],
    target_branch: str,
) -> list[WorktreeInfo]:
    """Find all worktrees where target_branch appears in the stack.

    Searches for worktrees where target_branch is either:
    - Checked out directly (exact match)
    - An ancestor or descendant in the worktree's Graphite stack

    Args:
        ctx: Workstack context with git and graphite operations
        repo_root: Path to the repository root
        worktrees: List of all worktrees from list_worktrees()
        target_branch: Branch name to search for

    Returns:
        List of WorktreeInfo objects where target_branch appears in the stack.
        Empty list if no worktrees contain the branch.

    Algorithm:
        1. For each worktree:
           a. Get the worktree's checked-out branch
           b. Skip worktrees with detached HEAD (branch=None)
           c. Check for exact match first
           d. If Graphite is available, get the full stack and check if target is in stack
           e. If yes to either check, add worktree to results
        2. Return all matching worktrees

    Example:
        Given stack: main → feature-1 → feature-2
        Worktree feature-work is on feature-2

        >>> worktrees = ctx.git_ops.list_worktrees(repo.root)
        >>> # Search for feature-1 (ancestor of feature-2)
        >>> matching = find_worktrees_containing_branch(ctx, repo.root, worktrees, "feature-1")
        >>> print([wt.path for wt in matching])
        [Path("/path/to/work/feature-work")]  # Found because feature-1 is in stack
    """
    matching_worktrees: list[WorktreeInfo] = []

    for wt in worktrees:
        # Skip worktrees with detached HEAD
        if wt.branch is None:
            continue

        # First check for exact match (works without Graphite)
        if wt.branch == target_branch:
            matching_worktrees.append(wt)
            continue

        # Then check if target is in the worktree's Graphite stack (if available)
        stack = ctx.graphite_ops.get_branch_stack(ctx.git_ops, repo_root, wt.branch)

        # Check if target_branch is in the stack
        if stack and target_branch in stack:
            matching_worktrees.append(wt)

    return matching_worktrees
