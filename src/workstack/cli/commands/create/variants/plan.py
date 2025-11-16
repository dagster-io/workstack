"""Plan creation variant implementation.

This module handles creating a worktree with a plan file.
The plan file is moved or copied to a .plan/ folder in the new worktree.
The worktree name is typically derived from the plan filename.
"""

from workstack.cli.commands.create.types import BranchConfig, CreationRequest, CreationResult
from workstack.cli.commands.create.worktree_ops import add_worktree
from workstack.cli.output import user_output
from workstack.core.context import WorkstackContext
from workstack.core.naming_utils import default_branch_for_worktree
from workstack.core.plan_folder import create_plan_folder


def create_with_plan(
    ctx: WorkstackContext,
    request: CreationRequest,
) -> CreationResult:
    """Handle --plan variant.

    Creates worktree with plan file. The plan is moved or copied
    to a .plan/ folder in the new worktree based on the keep_source flag.

    Args:
        ctx: Workstack context
        request: Creation request with all parameters

    Returns:
        CreationResult with branch configuration and plan destination

    Raises:
        ValueError: If plan_config is None (programming error)
    """
    if request.plan_config is None:
        raise ValueError("plan variant requires plan_config to be set")

    target = request.target

    # Derive branch name if not provided
    branch = request.branch_override or default_branch_for_worktree(target.name)

    # Get graphite setting from global config
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False

    # Create worktree
    add_worktree(
        ctx,
        target.repo_root,
        target.path,
        branch=branch,
        ref=request.ref,
        use_graphite=use_graphite,
        use_existing_branch=False,
    )

    # Read plan content from source file
    if request.plan_config.source_file is None:
        raise ValueError("plan_config.source_file cannot be None in create_with_plan")

    plan_content = request.plan_config.source_file.read_text(encoding="utf-8")

    # Create .plan/ folder in new worktree
    plan_folder_destination = create_plan_folder(target.path, plan_content)

    # Handle --keep-plan flag
    if request.plan_config.keep_source:
        if request.output.mode == "human":
            user_output(f"Copied plan to {plan_folder_destination}")
    else:
        request.plan_config.source_file.unlink()  # Remove source file
        if request.output.mode == "human":
            user_output(f"Moved plan to {plan_folder_destination}")

    # Build result
    branch_config = BranchConfig(
        branch=branch,
        ref=request.ref,
        use_existing_branch=False,
        use_graphite=use_graphite,
    )

    return CreationResult(branch_config=branch_config, plan_dest=plan_folder_destination)
