"""CLI command entry point for land-stack."""

import subprocess

import click

from workstack.cli.commands.land_stack.cleanup import _cleanup_and_navigate
from workstack.cli.commands.land_stack.discovery import _get_branches_to_land
from workstack.cli.commands.land_stack.display import _show_final_state, _show_landing_plan
from workstack.cli.commands.land_stack.execution import _land_branch_sequence
from workstack.cli.commands.land_stack.output import _emit
from workstack.cli.commands.land_stack.validation import (
    _validate_branches_have_prs,
    _validate_landing_preconditions,
    _validate_pr_mergeability,
)
from workstack.cli.core import discover_repo_context
from workstack.core.context import WorkstackContext


@click.command("land-stack")
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Skip confirmation prompt and proceed immediately.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show detailed output for merge and sync operations.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be done without executing merge operations.",
)
@click.option(
    "--script",
    is_flag=True,
    hidden=True,
    help="Output shell script for directory change instead of messages.",
)
@click.pass_obj
def land_stack(
    ctx: WorkstackContext, force: bool, verbose: bool, dry_run: bool, script: bool
) -> None:
    """Land all PRs from bottom of stack up to and including current branch.

    This command merges all PRs sequentially from the bottom of the stack (first
    branch above trunk) up to the current branch, running 'gt sync -f' between
    each merge to restack remaining branches.

    PRs are landed bottom-up because each PR depends on the ones below it.

    Requirements:
    - Graphite must be enabled (use-graphite config)
    - Clean working directory (no uncommitted changes)
    - All branches must have open PRs
    - Current branch must not be a trunk branch

    Example:
        Stack: main → feat-1 → feat-2 → feat-3
        Current branch: feat-3 (at top)
        Result: Lands feat-1, feat-2, feat-3 (in that order, bottom to top)
    """
    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)

    # Get current branch
    current_branch = ctx.git_ops.get_current_branch(ctx.cwd)

    # Get branches to land
    branches_to_land = _get_branches_to_land(ctx, repo.root, current_branch or "")

    # Validate preconditions
    _validate_landing_preconditions(
        ctx, repo.root, current_branch, branches_to_land, script_mode=script
    )

    # Validate all branches have open PRs
    valid_branches = _validate_branches_have_prs(
        ctx, repo.root, branches_to_land, script_mode=script
    )

    # Validate no merge conflicts
    _validate_pr_mergeability(ctx, repo.root, valid_branches, script_mode=script)

    # Get trunk branch (parent of first branch to land)
    if not valid_branches:
        _emit("No branches to land.", script_mode=script, error=True)
        raise SystemExit(1)

    first_branch = valid_branches[0][0]  # First tuple is (branch, pr_number, title)
    trunk_branch = ctx.graphite_ops.get_parent_branch(ctx.git_ops, repo.root, first_branch)
    if trunk_branch is None:
        error_msg = f"Error: Could not determine trunk branch for {first_branch}"
        _emit(error_msg, script_mode=script, error=True)
        raise SystemExit(1)

    # Show plan and get confirmation
    _show_landing_plan(
        current_branch or "",
        trunk_branch,
        valid_branches,
        force=force,
        dry_run=dry_run,
        script_mode=script,
    )

    # Execute landing sequence
    try:
        merged_branches = _land_branch_sequence(
            ctx, repo.root, valid_branches, verbose=verbose, dry_run=dry_run, script_mode=script
        )
    except subprocess.CalledProcessError as e:
        _emit("", script_mode=script)
        # Show full stderr from subprocess for complete error context
        error_detail = e.stderr.strip() if e.stderr else str(e)
        error_msg = click.style(f"❌ Landing stopped: {error_detail}", fg="red")
        _emit(error_msg, script_mode=script, error=True)
        raise SystemExit(1) from None
    except FileNotFoundError as e:
        _emit("", script_mode=script)
        error_msg = click.style(
            f"❌ Command not found: {e.filename}\n\n"
            "Install required tools:\n"
            "  • GitHub CLI: brew install gh\n"
            "  • Graphite CLI: brew install withgraphite/tap/graphite",
            fg="red",
        )
        _emit(error_msg, script_mode=script, error=True)
        raise SystemExit(1) from None

    # All succeeded - run cleanup operations
    final_branch = _cleanup_and_navigate(
        ctx,
        repo.root,
        merged_branches,
        trunk_branch,
        verbose=verbose,
        dry_run=dry_run,
        script_mode=script,
    )

    # Show final state
    _emit("", script_mode=script)
    _show_final_state(merged_branches, final_branch, dry_run=dry_run, script_mode=script)
