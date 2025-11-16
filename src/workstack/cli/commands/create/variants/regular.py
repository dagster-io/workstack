"""Regular creation variant implementation.

This module handles standard worktree creation with optional Graphite integration.
This is the default variant when no special flags are provided.
"""

from workstack.cli.commands.create.types import BranchConfig, CreationRequest, CreationResult
from workstack.cli.commands.create.worktree_ops import add_worktree
from workstack.core.context import WorkstackContext
from workstack.core.naming_utils import default_branch_for_worktree


def create_regular(
    ctx: WorkstackContext,
    request: CreationRequest,
) -> CreationResult:
    """Handle regular creation variant.

    Standard worktree creation with optional Graphite integration.
    Derives branch name from worktree name if not explicitly provided.

    Args:
        ctx: Workstack context
        request: Creation request with all parameters

    Returns:
        CreationResult with branch configuration
    """
    target = request.target

    # Derive branch name if not provided
    branch = request.branch_override or default_branch_for_worktree(target.name)

    # Get graphite setting from global config
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False

    # Create the worktree
    add_worktree(
        ctx,
        target.repo_root,
        target.path,
        branch=branch,
        ref=request.ref,
        use_graphite=use_graphite,
        use_existing_branch=False,
    )

    # Build result
    branch_config = BranchConfig(
        branch=branch,
        ref=request.ref,
        use_existing_branch=False,
        use_graphite=use_graphite,
    )

    return CreationResult(branch_config=branch_config)
