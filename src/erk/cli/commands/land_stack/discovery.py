"""Stack discovery and graph traversal for land-stack."""

from pathlib import Path

from erk.core.context import WorkstackContext
from erk.core.graphite_ops import BranchMetadata


def _get_branches_to_land(
    ctx: WorkstackContext, repo_root: Path, current_branch: str, down_only: bool = False
) -> list[str]:
    """Get branches to land from stack.

    By default, lands entire stack (trunk to leaf). With down_only=True, lands only
    downstack branches (trunk to current).

    For PR landing, we need to land from the bottom (closest to trunk) upward,
    as each PR depends on the one below it.

    Args:
        ctx: WorkstackContext with access to graphite operations
        repo_root: Repository root directory
        current_branch: Name of the current branch
        down_only: If True, only return branches from trunk to current.
                   If False, return entire stack (trunk to leaf).

    Returns:
        List of branch names from bottom of stack to target (inclusive, excluding trunk)
        Empty list if branch not in stack
    """
    # Get full stack (trunk to leaves)
    stack = ctx.graphite_ops.get_branch_stack(ctx.git_ops, repo_root, current_branch)
    if stack is None:
        return []

    # Get all branch metadata to filter out trunk branches
    all_branches = ctx.graphite_ops.get_all_branches(ctx.git_ops, repo_root)
    if not all_branches:
        return []

    # Filter stack to exclude trunk branches
    filtered_stack = [b for b in stack if b in all_branches and not all_branches[b].is_trunk]

    # Find current branch index
    if current_branch not in filtered_stack:
        return []

    if down_only:
        # Return slice from start to current (inclusive) - bottom to current for PR landing
        current_idx = filtered_stack.index(current_branch)
        return filtered_stack[: current_idx + 1]

    # Return entire stack (trunk to leaf)
    return filtered_stack


def _get_all_children(branch: str, all_branches: dict[str, BranchMetadata]) -> list[str]:
    """Get all children (upstack branches) of a branch recursively.

    Args:
        branch: Branch name to get children for
        all_branches: Dict of all branch metadata from get_all_branches()

    Returns:
        List of all children branch names (direct and indirect), in order from
        closest to furthest upstack. Returns empty list if branch has no children.
    """
    result: list[str] = []

    branch_metadata = all_branches.get(branch)
    if not branch_metadata or not branch_metadata.children:
        return result

    # Process direct children
    for child in branch_metadata.children:
        result.append(child)
        # Recursively get children of children
        result.extend(_get_all_children(child, all_branches))

    return result
