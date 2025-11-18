"""Reroot planning utilities for forest operations."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from erk.core.forest_types import Forest
from erk.core.graphite_ops import GraphiteOps

# Conflict commit format with SHA
CONFLICT_COMMIT_PREFIX = "[CONFLICT] Rebase conflicts from"
RESOLVED_COMMIT_PREFIX = "[RESOLVED] Fix rebase conflicts from"


@dataclass(frozen=True)
class RerootPlan:
    """Plan for rerooting a forest."""

    forest_name: str
    branches_in_order: list[tuple[str, str]]  # (branch, parent) pairs
    target_base: str  # Trunk branch to rebase onto
    total_branches: int  # For progress tracking


@dataclass(frozen=True)
class RerootMarker:
    """Marker file content for .erk/REROOT_IN_PROGRESS."""

    forest: str
    started_at: str  # ISO 8601
    current_branch: str


def create_reroot_plan(
    forest: Forest,
    graphite_ops: GraphiteOps,
    git_ops,
    trunk_branch: str,
    repo_root: Path,
) -> RerootPlan:
    """Create reroot plan with branch order (bottom to top).

    Args:
        forest: Forest to reroot
        graphite_ops: GraphiteOps for stack information
        git_ops: GitOps for git operations
        trunk_branch: Trunk branch name
        repo_root: Repository root path

    Returns:
        Reroot plan with branches ordered from trunk to leaves
    """
    if not forest.worktrees:
        raise ValueError(f"Forest '{forest.name}' has no worktrees")

    # Get stack for first worktree's branch
    first_branch = forest.worktrees[0]
    stack = graphite_ops.get_branch_stack(git_ops, repo_root, first_branch)

    if stack is None:
        raise ValueError(f"Could not get stack for branch '{first_branch}'")

    # Filter to only branches in the forest
    forest_branches = [b for b in stack if b in forest.worktrees or b == trunk_branch]

    # Create (branch, parent) pairs
    # Skip trunk itself (it's the base)
    branches_in_order = []

    for i, branch in enumerate(forest_branches):
        if branch == trunk_branch:
            continue

        # Parent is previous branch in stack
        if i > 0:
            parent = forest_branches[i - 1]
            branches_in_order.append((branch, parent))

    return RerootPlan(
        forest_name=forest.name,
        branches_in_order=branches_in_order,
        target_base=trunk_branch,
        total_branches=len(branches_in_order),
    )


def format_conflict_commit_message(parent_branch: str, parent_sha: str) -> str:
    """Format commit message for conflict state.

    Args:
        parent_branch: Parent branch name
        parent_sha: Parent commit SHA (will be truncated to 7 chars)

    Returns:
        Formatted commit message
    """
    return f"{CONFLICT_COMMIT_PREFIX} {parent_branch} ({parent_sha[:7]})"


def format_resolved_commit_message(parent_branch: str, parent_sha: str) -> str:
    """Format commit message for resolution state.

    Args:
        parent_branch: Parent branch name
        parent_sha: Parent commit SHA (will be truncated to 7 chars)

    Returns:
        Formatted commit message
    """
    return f"{RESOLVED_COMMIT_PREFIX} {parent_branch} ({parent_sha[:7]})"


def detect_conflict_markers(file_path: Path) -> bool:
    """Check if file contains git conflict markers.

    Args:
        file_path: Path to file to check

    Returns:
        True if file contains conflict markers
    """
    if not file_path.exists():
        return False

    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Check for git conflict markers
        return "<<<<<<<" in content or "=======" in content or ">>>>>>>" in content
    except OSError:
        return False


def create_reroot_marker(forest_name: str, current_branch: str) -> RerootMarker:
    """Create marker for .erk/REROOT_IN_PROGRESS file.

    Args:
        forest_name: Name of forest being rerooted
        current_branch: Current branch being processed

    Returns:
        RerootMarker instance
    """
    return RerootMarker(
        forest=forest_name,
        started_at=datetime.now(UTC).isoformat(),
        current_branch=current_branch,
    )


def format_progress_message(current: int, total: int, branch_name: str) -> str:
    """Format progress indicator for reroot output.

    Args:
        current: Current branch number (1-indexed)
        total: Total number of branches
        branch_name: Name of branch being processed

    Returns:
        Formatted progress message
    """
    return f"Processing branch {current}/{total}: {branch_name}"
