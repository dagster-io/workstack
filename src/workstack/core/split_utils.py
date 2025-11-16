"""Pure business logic for worktree split operations.

This module contains the core logic for determining which worktrees need to be
created when splitting a Graphite stack from a single worktree into individual
worktrees per branch. All functions are pure and testable without filesystem I/O.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from workstack.core.gitops import WorktreeInfo


@dataclass(frozen=True)
class SplitPlan:
    """Plan for splitting a stack into individual worktrees.

    Attributes:
        stack_branches: Full list of branches in the stack (trunk to leaf)
        branches_to_split: Subset of branches needing worktrees
        existing_worktrees: Branches that already have worktrees (informational)
        target_paths: Mapping of branch names to their target worktree paths
        source_worktree_path: Path to the source worktree where we're splitting from
        repo_root: Path to the repository root
        skipped_current: True if current branch was skipped (already checked out)
        skipped_trunk: True if trunk branch was skipped (stays in root worktree)
    """

    stack_branches: list[str]
    branches_to_split: list[str]
    existing_worktrees: list[str]
    target_paths: dict[str, Path]
    source_worktree_path: Path
    repo_root: Path
    skipped_current: bool
    skipped_trunk: bool


def identify_splittable_branches(
    stack_branches: list[str],
    trunk_branch: str,
    current_branch: str | None,
    all_worktrees: list[WorktreeInfo],
) -> tuple[list[str], list[str], bool, bool]:
    """Identify which branches need new worktrees.

    A branch needs a worktree if:
    1. It's not the trunk branch (trunk stays in root worktree)
    2. It's not the currently checked out branch (git prevents duplicate checkouts)
    3. It doesn't already have a worktree

    Args:
        stack_branches: Full stack from trunk to leaf
        trunk_branch: The trunk branch name (main or master)
        current_branch: Currently checked out branch (None if detached)
        all_worktrees: All existing worktrees in the repository

    Returns:
        Tuple of (branches_to_split, existing_worktrees, skipped_current, skipped_trunk)
        - branches_to_split: Branches that need new worktrees
        - existing_worktrees: Branches that already have worktrees
        - skipped_current: True if current branch was skipped
        - skipped_trunk: True if trunk branch was skipped
    """
    branches_to_split = []
    existing_worktrees = []
    skipped_current = False
    skipped_trunk = False

    # Build set of branches that already have worktrees
    branches_with_worktrees = {wt.branch for wt in all_worktrees if wt.branch is not None}

    for branch in stack_branches:
        # Track if this branch is trunk and/or current (can be both)
        is_trunk = branch == trunk_branch
        is_current = branch == current_branch

        # Skip trunk branch - it stays in root worktree
        if is_trunk:
            skipped_trunk = True

        # Skip current branch - can't create worktree for checked out branch
        if is_current:
            skipped_current = True

        # Skip this branch if it's trunk or current
        if is_trunk or is_current:
            continue

        # Check if branch already has a worktree
        if branch in branches_with_worktrees:
            existing_worktrees.append(branch)
        else:
            branches_to_split.append(branch)

    return branches_to_split, existing_worktrees, skipped_current, skipped_trunk


def create_split_plan(
    stack_branches: list[str],
    trunk_branch: str,
    current_branch: str | None,
    all_worktrees: list[WorktreeInfo],
    workstacks_dir: Path,
    sanitize_worktree_name: Callable[[str], str],
    source_worktree_path: Path,
    repo_root: Path,
) -> SplitPlan:
    """Create a complete split plan.

    Args:
        stack_branches: Full stack from trunk to leaf
        trunk_branch: The trunk branch name (main or master)
        current_branch: Currently checked out branch (None if detached)
        all_worktrees: All existing worktrees in the repository
        workstacks_dir: Base directory for workstack worktrees
        sanitize_worktree_name: Function to convert branch name to valid worktree name
        source_worktree_path: Path to the current worktree we're splitting from
        repo_root: Path to the repository root

    Returns:
        Complete split plan with all information needed for execution
    """
    result = identify_splittable_branches(
        stack_branches, trunk_branch, current_branch, all_worktrees
    )
    branches_to_split, existing_worktrees, skipped_current, skipped_trunk = result

    # Build target paths for branches needing worktrees
    target_paths = {}
    for branch in branches_to_split:
        worktree_name = sanitize_worktree_name(branch)
        target_paths[branch] = workstacks_dir / worktree_name

    return SplitPlan(
        stack_branches=stack_branches,
        branches_to_split=branches_to_split,
        existing_worktrees=existing_worktrees,
        target_paths=target_paths,
        source_worktree_path=source_worktree_path,
        repo_root=repo_root,
        skipped_current=skipped_current,
        skipped_trunk=skipped_trunk,
    )


def execute_split_plan(
    plan: SplitPlan,
    git_ops,  # Type annotation omitted to avoid circular import
) -> list[tuple[str, Path]]:
    """Execute a split plan by creating worktrees.

    The actual execution depends on the GitOps implementation passed in:
    - RealGitOps: Actually creates the worktrees
    - NoopGitOps: No-op execution for dry-run mode
    - PrintingGitOps: Prints operations (wraps either Real or Noop)

    Args:
        plan: The split plan to execute
        git_ops: GitOps instance for performing git operations

    Returns:
        List of (branch, worktree_path) tuples indicating what was processed
    """
    results = []

    for branch in plan.branches_to_split:
        target_path = plan.target_paths[branch]

        # Create worktree for existing branch
        # Using create_branch=False since branch already exists
        # The actual behavior depends on the injected GitOps implementation
        git_ops.add_worktree(
            plan.repo_root,
            target_path,
            branch=branch,
            ref=None,
            create_branch=False,
        )

        results.append((branch, target_path))

    return results
