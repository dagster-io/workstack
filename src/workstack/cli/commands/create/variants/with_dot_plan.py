"""With-dot-plan creation variant implementation.

This module handles copying a .plan/ folder from a source workstack
and creating a sibling branch using Graphite. This is the most
complex variant due to source resolution and Graphite integration.
"""

import click

from workstack.cli.commands.create.types import BranchConfig, CreationRequest, CreationResult
from workstack.cli.commands.create.worktree_ops import add_worktree, copy_plan_folder
from workstack.cli.output import user_output
from workstack.core.context import WorkstackContext
from workstack.core.naming_utils import default_branch_for_worktree


def create_with_dot_plan(
    ctx: WorkstackContext,
    request: CreationRequest,
) -> CreationResult:
    """Handle --with-dot-plan variant.

    Copies .plan/ folder from source workstack, creates sibling branch
    using Graphite. The new worktree becomes a sibling to the source
    workstack's branch.

    Args:
        ctx: Workstack context
        request: Creation request with all parameters

    Returns:
        CreationResult with branch configuration and source name

    Raises:
        ValueError: If dot_plan_source is None (programming error)
    """
    if request.dot_plan_source is None:
        raise ValueError("with_dot_plan variant requires dot_plan_source to be set")

    target = request.target
    source = request.dot_plan_source

    # Derive branch name if not provided
    branch = request.branch_override or default_branch_for_worktree(target.name)

    # Display explanatory output for human mode
    if request.output.mode == "human":
        user_output("")
        user_output(f"Copying plan from {click.style(source.name, fg='cyan', bold=True)}")
        user_output(f"  Source branch: {click.style(source.branch, fg='yellow')}")
        user_output(f"  Parent branch: {click.style(source.parent_branch, fg='yellow')}")
        user_output("  New worktree will be sibling to source")
        user_output("")

    # Create worktree based on parent branch, using Graphite
    # This creates a sibling branch to the source branch
    add_worktree(
        ctx,
        target.repo_root,
        target.path,
        branch=branch,
        ref=source.parent_branch,
        use_existing_branch=False,
        use_graphite=True,
    )

    # Copy plan folder from source workstack
    copy_plan_folder(source.path, target.path)

    if request.output.mode == "human":
        user_output(click.style("✓", fg="green") + f" Copied .plan/ folder from {source.name}")

    # Build result
    branch_config = BranchConfig(
        branch=branch,
        ref=source.parent_branch,
        use_existing_branch=False,
        use_graphite=True,
    )

    return CreationResult(branch_config=branch_config, source_name=source.name)
