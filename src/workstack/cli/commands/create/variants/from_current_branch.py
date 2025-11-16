"""From-current-branch creation variant implementation.

This module handles moving the current branch to a new worktree,
while switching the current worktree to the parent branch (or ref/trunk).
This is a two-phase operation and one of the more complex variants.
"""

from workstack.cli.commands.create.types import BranchConfig, CreationRequest, CreationResult
from workstack.cli.commands.create.worktree_ops import add_worktree
from workstack.cli.output import user_output
from workstack.core.context import WorkstackContext


def create_from_current_branch(
    ctx: WorkstackContext,
    request: CreationRequest,
) -> CreationResult:
    """Handle --from-current-branch variant.

    Moves current branch to new worktree, switches current worktree
    to parent/ref/trunk. This is a two-phase operation:
    1. Switch current worktree to another branch (parent/ref/trunk)
    2. Create new worktree with the original current branch

    Args:
        ctx: Workstack context
        request: Creation request with all parameters

    Returns:
        CreationResult with branch configuration

    Raises:
        SystemExit: If current branch is detached or same as target
    """
    target = request.target

    # Get the current branch
    current_branch = ctx.git_ops.get_current_branch(ctx.cwd)
    if current_branch is None:
        user_output("Error: HEAD is detached (not on a branch)")
        raise SystemExit(1)

    # Determine preferred branch to checkout (prioritize Graphite parent)
    parent_branch = (
        ctx.graphite_ops.get_parent_branch(ctx.git_ops, target.repo_root, current_branch)
        if current_branch
        else None
    )

    if parent_branch:
        # Prefer Graphite parent branch
        to_branch = parent_branch
    elif request.ref:
        # Use ref if provided
        to_branch = request.ref
    else:
        # Fall back to default branch (main/master)
        to_branch = ctx.git_ops.detect_default_branch(target.repo_root, ctx.trunk_branch)

    # Check for edge case: can't move main to worktree then switch to main
    if current_branch == to_branch:
        user_output(
            f"Error: Cannot use --from-current-branch when on '{current_branch}'.\n"
            f"The current branch cannot be moved to a worktree and then checked out again.\n\n"
            f"Alternatives:\n"
            f"  • Create a new branch: workstack create {target.name}\n"
            f"  • Switch to a feature branch first, then use --from-current-branch\n"
            f"  • Use --from-branch to create from a different existing branch",
        )
        raise SystemExit(1)

    # Phase 1: Switch current worktree to another branch
    # Check if target branch is available (not checked out in another worktree)
    checkout_path = ctx.git_ops.is_branch_checked_out(target.repo_root, to_branch)
    if checkout_path is not None:
        # Target branch is in use, fall back to detached HEAD
        ctx.git_ops.checkout_detached(ctx.cwd, current_branch)
    else:
        # Target branch is available, checkout normally
        ctx.git_ops.checkout_branch(ctx.cwd, to_branch)

    # Phase 2: Create worktree with the original current branch
    add_worktree(
        ctx,
        target.repo_root,
        target.path,
        branch=current_branch,
        ref=None,
        use_existing_branch=True,
        use_graphite=False,
    )

    # Build result
    branch_config = BranchConfig(
        branch=current_branch,
        ref=None,
        use_existing_branch=True,
        use_graphite=False,
    )

    return CreationResult(branch_config=branch_config)
