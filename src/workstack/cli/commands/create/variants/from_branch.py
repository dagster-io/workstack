"""From-branch creation variant implementation.

This module handles creation of a worktree from an existing branch.
This is the simplest variant, as it just checks out an existing branch
in a new worktree location.
"""

from workstack.cli.commands.create.types import BranchConfig, CreationRequest, CreationResult
from workstack.cli.commands.create.worktree_ops import add_worktree
from workstack.core.context import WorkstackContext


def create_from_branch(
    ctx: WorkstackContext,
    request: CreationRequest,
) -> CreationResult:
    """Handle --from-branch variant.

    Creates worktree from an existing branch. The branch must already
    exist in the repository.

    Args:
        ctx: Workstack context
        request: Creation request with all parameters

    Returns:
        CreationResult with branch configuration

    Note:
        The branch name comes from the --from-branch flag value,
        which is passed through the orchestrator's name derivation logic
        and ends up in request.target.name.
    """
    target = request.target

    # For from_branch variant, the branch name is derived from
    # the --from-branch value during orchestration
    branch_name = request.branch_override

    if not branch_name:
        raise ValueError("from_branch variant requires branch_override to be set")

    # Create worktree with existing branch
    add_worktree(
        ctx,
        target.repo_root,
        target.path,
        branch=branch_name,
        ref=None,
        use_existing_branch=True,
        use_graphite=False,
    )

    # Build result
    branch_config = BranchConfig(
        branch=branch_name,
        ref=None,
        use_existing_branch=True,
        use_graphite=False,
    )

    return CreationResult(branch_config=branch_config)
