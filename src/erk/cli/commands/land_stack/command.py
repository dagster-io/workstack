"""CLI command entry point for land-stack."""

import dataclasses
import logging
import os
import subprocess

import click

from erk.cli.commands.land_stack.cleanup import _cleanup_and_navigate
from erk.cli.commands.land_stack.discovery import _get_branches_to_land
from erk.cli.commands.land_stack.display import _show_final_state, _show_landing_plan
from erk.cli.commands.land_stack.execution import land_branch_sequence
from erk.cli.commands.land_stack.output import _emit
from erk.cli.commands.land_stack.validation import (
    _validate_branches_have_prs,
    _validate_landing_preconditions,
    _validate_pr_mergeability,
)
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel

logger = logging.getLogger(__name__)

# Enable debug logging if ERK_DEBUG environment variable is set
if os.getenv("ERK_DEBUG"):
    logging.basicConfig(level=logging.DEBUG, format="[DEBUG %(name)s:%(lineno)d] %(message)s")


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
    "--down",
    is_flag=True,
    help="Only land branches downstack (toward trunk) from current branch. Skips upstack rebase.",
)
@click.option(
    "--script",
    is_flag=True,
    hidden=True,
    help="Output shell script for directory change instead of messages.",
)
@click.pass_obj
def land_stack(
    ctx: ErkContext, force: bool, verbose: bool, dry_run: bool, down: bool, script: bool
) -> None:
    """Land all PRs in stack.

    By default, lands full stack (trunk to leaf). With --down, lands only
    downstack PRs (trunk to current branch).

    This command merges all PRs sequentially from the bottom of the stack (first
    branch above trunk) upward. After each merge, it runs 'gt sync -f' to rebase
    upstack branches onto the updated trunk. With --down, skips the rebase and
    force-push of upstack branches entirely.

    PRs are landed bottom-up because each PR depends on the ones below it.

    Use --down when you have uncommitted changes or work-in-progress in upstack
    branches that you don't want to rebase yet.

    Requirements:
    - Graphite must be enabled (use-graphite config)
    - Clean working directory (no uncommitted changes)
    - All branches must have open PRs
    - Current branch must not be a trunk branch

    Example (default - full stack):
        Stack: main → feat-1 → feat-2 → feat-3
        Current branch: feat-2
        Result: Lands feat-1, feat-2, feat-3 (full stack)

    Example (--down - downstack only):
        Stack: main → feat-1 → feat-2 → feat-3
        Current branch: feat-2
        Result: Lands feat-1, feat-2 (downstack only, feat-3 untouched)

    Example (current at top of stack):
        Stack: main → feat-1 → feat-2 → feat-3
        Current branch: feat-3 (at the top of the stack)
        Result: Lands feat-1, feat-2, feat-3 (same with or without --down)
    """
    logger.debug(
        "Command invoked: land_stack(force=%s, dry_run=%s, down=%s, script=%s, current_dir=%s)",
        force,
        dry_run,
        down,
        script,
        ctx.cwd,
    )
    repo_root = ctx.repo.root if not isinstance(ctx.repo, NoRepoSentinel) else None
    logger.debug("Context: repo_root=%s, trunk_branch=%s", repo_root, ctx.trunk_branch)

    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)
    logger.debug("Repository discovered: root=%s", repo.root if repo else None)
    from erk.core.git.dry_run import DryRunGit
    from erk.core.git.printing import PrintingGit
    from erk.core.github.dry_run import DryRunGitHub
    from erk.core.github.printing import PrintingGitHub
    from erk.core.graphite.dry_run import DryRunGraphite
    from erk.core.graphite.printing import PrintingGraphite

    # First: Choose inner implementation based on dry-run mode
    if dry_run:
        # Wrap with Noop (makes operations no-op)
        inner_git_ops = DryRunGit(ctx.git)
        inner_github_ops = DryRunGitHub(ctx.github)
        inner_graphite_ops = DryRunGraphite(ctx.graphite)
    else:
        # Use real implementations
        inner_git_ops = ctx.git
        inner_github_ops = ctx.github
        inner_graphite_ops = ctx.graphite

    # Then: Always wrap with Printing layer (adds output for all operations)
    ctx = dataclasses.replace(
        ctx,
        git=PrintingGit(inner_git_ops, script_mode=script, dry_run=dry_run),
        github=PrintingGitHub(inner_github_ops, script_mode=script, dry_run=dry_run),
        graphite=PrintingGraphite(inner_graphite_ops, script_mode=script, dry_run=dry_run),
    )

    # Get current branch
    current_branch = ctx.git.get_current_branch(ctx.cwd)
    logger.debug("Current branch detected: %s", current_branch)

    # Get branches to land
    branches_to_land = _get_branches_to_land(ctx, repo.root, current_branch or "", down_only=down)
    logger.debug("Branches to land: count=%d, branches=%s", len(branches_to_land), branches_to_land)

    # Validate preconditions
    _validate_landing_preconditions(
        ctx, repo.root, current_branch, branches_to_land, down, script_mode=script
    )

    # Validate all branches have open PRs
    valid_branches = _validate_branches_have_prs(
        ctx, repo.root, branches_to_land, script_mode=script
    )

    # Get trunk branch (parent of first branch to land)
    # Must get this BEFORE validation so we can pass it to _validate_pr_mergeability
    if not valid_branches:
        _emit("No branches to land.", script_mode=script, error=True)
        raise SystemExit(1)

    first_branch = valid_branches[0][0]  # First tuple is (branch, pr_number, title)
    trunk_branch = ctx.graphite.get_parent_branch(ctx.git, repo.root, first_branch)
    if trunk_branch is None:
        error_msg = f"Error: Could not determine trunk branch for {first_branch}"
        _emit(error_msg, script_mode=script, error=True)
        raise SystemExit(1)

    # Validate no merge conflicts (now with correct trunk_branch)
    _validate_pr_mergeability(ctx, repo.root, valid_branches, trunk_branch, script_mode=script)

    # Show plan and get confirmation
    logger.debug("About to show landing plan: branches=%d, force=%s", len(valid_branches), force)
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
        merged_branches = land_branch_sequence(
            ctx,
            repo.root,
            valid_branches,
            verbose=verbose,
            dry_run=dry_run,
            down_only=down,
            script_mode=script,
        )
    except subprocess.CalledProcessError as e:
        logger.debug("Exception caught: %s: %s", type(e).__name__, str(e))
        logger.debug("Exception details:", exc_info=True)
        _emit("", script_mode=script)
        # Show full stderr from subprocess for complete error context
        error_detail = e.stderr.strip() if e.stderr else str(e)
        error_msg = click.style(f"❌ Landing stopped: {error_detail}", fg="red")
        _emit(error_msg, script_mode=script, error=True)
        raise SystemExit(1) from None
    except FileNotFoundError as e:
        logger.debug("Exception caught: %s: %s", type(e).__name__, str(e))
        logger.debug("Exception details:", exc_info=True)
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
    final_branch, final_path = _cleanup_and_navigate(
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

    # Generate activation script for shell integration
    if script:
        from erk.cli.shell_utils import render_navigation_script

        # After cleanup, we're at final worktree (trunk or child)
        # Generate navigation script to switch shell to final worktree
        # Uses render_navigation_script to automatically choose between cd (root)
        # or full activation (worktree)
        script_content = render_navigation_script(
            final_path,
            repo.root,
            comment=f"land-stack: switch to {final_branch}",
            success_message=f"✓ Switched to {final_branch} at {final_path}",
        )
        result = ctx.script_writer.write_activation_script(
            script_content,
            command_name="land-stack",
            comment=f"switch to {final_branch}",
        )
        result.output_for_shell_integration()
