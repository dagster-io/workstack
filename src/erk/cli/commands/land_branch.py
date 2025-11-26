"""Land a single PR and navigate to next branch in stack.

This command:
1. Validates the branch is exactly one level up from trunk
2. Checks an open pull request exists
3. Squash-merges the PR to trunk
4. Optionally navigates to child (default) or parent (--down) branch
5. Optionally deletes the merged branch and worktree (--cleanup)

Usage:
    erk land-branch              # Merge and navigate to child
    erk land-branch --down       # Merge and navigate to parent
    erk land-branch --cleanup    # Merge, navigate, and delete worktree
"""

from pathlib import Path

import click
from erk_shared.output.output import user_output

from erk.cli.commands.navigation_helpers import (
    activate_root_repo,
    activate_worktree,
    check_clean_working_tree,
    delete_branch_and_worktree,
    ensure_graphite_enabled,
    resolve_down_navigation,
    resolve_up_navigation,
)
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext


def _validate_branch_and_pr(
    ctx: ErkContext, repo: RepoContext, current_branch: str, trunk_branch: str | None
) -> int:
    """Validate branch is one level from trunk and has an open PR.

    Args:
        ctx: Erk context
        repo: Repository context
        current_branch: Current branch name
        trunk_branch: Configured trunk branch name

    Returns:
        PR number of the open PR

    Raises:
        SystemExit: If validation fails
    """
    # Get parent branch
    parent_branch = ctx.graphite.get_parent_branch(ctx.git, repo.root, current_branch)
    if parent_branch is None:
        user_output(
            click.style("Error: ", fg="red")
            + f"Could not determine parent branch for: {current_branch}"
        )
        raise SystemExit(1)

    # Validate parent is trunk
    detected_trunk = ctx.git.detect_default_branch(repo.root, trunk_branch)
    if parent_branch != detected_trunk:
        user_output(
            click.style("Error: ", fg="red")
            + f"Branch must be exactly one level up from {detected_trunk}\n"
            f"Current branch: {current_branch}\n"
            f"Parent branch: {parent_branch} (expected: {detected_trunk})\n\n"
            f"Please navigate to a branch that branches directly from {detected_trunk}."
        )
        raise SystemExit(1)

    # Check PR exists and is open
    pr_info = ctx.github.get_pr_status(repo.root, current_branch, debug=False)

    if pr_info.state == "NONE" or pr_info.pr_number is None:
        user_output(
            click.style("Error: ", fg="red") + "No pull request found for this branch\n\n"
            "Please create a PR first using: gt submit"
        )
        raise SystemExit(1)

    if pr_info.state != "OPEN":
        user_output(
            click.style("Error: ", fg="red")
            + f"Pull request is not open (state: {pr_info.state})\n\n"
            "This command only works with open pull requests."
        )
        raise SystemExit(1)

    return pr_info.pr_number


def _resolve_navigation_target(
    ctx: ErkContext,
    repo: RepoContext,
    current_branch: str,
    children: list[str],
    down: bool,
    cleanup: bool,
    script: bool,
    trunk_branch: str | None,
    current_worktree_path: Path | None,
) -> tuple[str, bool]:
    """Resolve the target branch for navigation.

    Args:
        ctx: Erk context
        repo: Repository context
        current_branch: Current branch name
        children: List of child branches
        down: Navigate down to parent instead of up to child
        cleanup: Whether cleanup is enabled
        script: Whether in script mode
        trunk_branch: Configured trunk branch name
        current_worktree_path: Path to current worktree (for cleanup)

    Returns:
        Tuple of (target_name, was_created)

    Raises:
        SystemExit: If multiple children exist and navigation should be skipped
    """
    worktrees = ctx.git.list_worktrees(repo.root)

    if down:
        # Navigate to parent (will go to trunk/root)
        return resolve_down_navigation(ctx, repo, current_branch, worktrees, trunk_branch)

    # Navigate to child (default)
    if len(children) == 0:
        # No children - navigate to trunk
        if script:
            ctx.feedback.info("No child branches, navigating to trunk")
        return "root", False

    if len(children) > 1:
        # Multiple children - skip navigation and inform user
        children_list = ", ".join(children)
        ctx.feedback.info(f"Multiple children detected: {children_list}")
        ctx.feedback.info("Run 'gt up' to interactively select a branch")
        if not cleanup:
            raise SystemExit(0)
        # If cleanup is enabled, cleanup then exit
        if current_worktree_path:
            delete_branch_and_worktree(ctx, repo.root, current_branch, current_worktree_path)
        raise SystemExit(0)

    # Single child - auto-navigate
    return resolve_up_navigation(ctx, repo, current_branch, worktrees)


def _activate_with_cleanup(
    ctx: ErkContext,
    repo: RepoContext,
    target_path: Path,
    script: bool,
    current_branch: str,
    current_worktree_path: Path,
) -> None:
    """Activate target worktree, perform cleanup, and exit.

    Args:
        ctx: Erk context
        repo: Repository context
        target_path: Path to target worktree
        script: Whether in script mode
        current_branch: Current branch name (to delete)
        current_worktree_path: Path to current worktree (to delete)

    Raises:
        SystemExit: Always (after successful activation and cleanup)
    """
    Ensure.path_exists(ctx, target_path, f"Worktree not found: {target_path}")

    if script:
        from erk_shared.output.output import machine_output

        from erk.cli.activation import render_activation_script

        activation_script = render_activation_script(worktree_path=target_path)
        result = ctx.script_writer.write_activation_script(
            activation_script,
            command_name="land-branch",
            comment=f"activate {target_path.name}",
        )
        machine_output(str(result.path), nl=False)
    else:
        ctx.feedback.info(
            "Shell integration not detected. Run 'erk init --shell' to set up automatic activation."
        )
        ctx.feedback.info("\nOr use: source <(erk land-branch --script)")

    # Perform cleanup
    delete_branch_and_worktree(ctx, repo.root, current_branch, current_worktree_path)
    raise SystemExit(0)


def _activate_root_with_cleanup(
    ctx: ErkContext,
    repo: RepoContext,
    script: bool,
    current_branch: str,
    current_worktree_path: Path,
) -> None:
    """Activate root repo, perform cleanup, and exit.

    Args:
        ctx: Erk context
        repo: Repository context
        script: Whether in script mode
        current_branch: Current branch name (to delete)
        current_worktree_path: Path to current worktree (to delete)

    Raises:
        SystemExit: Always (after successful activation and cleanup)
    """
    root_path = repo.root
    if script:
        from erk_shared.output.output import machine_output

        from erk.cli.activation import render_activation_script

        script_content = render_activation_script(
            worktree_path=root_path,
            final_message='echo "Switched to root repo: $(pwd)"',
            comment="work activate-script (root repo)",
        )
        result = ctx.script_writer.write_activation_script(
            script_content,
            command_name="land-branch",
            comment="activate root",
        )
        machine_output(str(result.path), nl=False)
    else:
        ctx.feedback.info(f"Switched to root repo: {root_path}")

    # Perform cleanup
    delete_branch_and_worktree(ctx, repo.root, current_branch, current_worktree_path)
    raise SystemExit(0)


@click.command("land-branch")
@click.option(
    "--script", is_flag=True, hidden=True, help="Output activation script for shell integration"
)
@click.option("--cleanup", is_flag=True, help="Delete current branch and worktree after landing")
@click.option(
    "--down", is_flag=True, help="Navigate to parent branch instead of child after landing"
)
@click.pass_obj
def land_branch_cmd(ctx: ErkContext, script: bool, cleanup: bool, down: bool) -> None:
    """Land a single PR and navigate to next branch in stack.

    This command safely lands a single branch from a Graphite stack by:
    1. Validating the branch is exactly one level up from trunk
    2. Checking an open pull request exists
    3. Squash-merging the PR to trunk
    4. Navigating to child branch (or parent with --down)

    With shell integration (recommended):
      erk land-branch

    Without shell integration:
      source <(erk land-branch --script)

    Requires Graphite to be enabled: 'erk config set use_graphite true'
    """
    ensure_graphite_enabled(ctx)
    repo = discover_repo_context(ctx, ctx.cwd)
    trunk_branch = ctx.trunk_branch

    # Get current branch
    current_branch = Ensure.not_none(
        ctx.git.get_current_branch(ctx.cwd), "Not currently on a branch (detached HEAD)"
    )

    # Validate branch and PR, get PR number
    pr_number = _validate_branch_and_pr(ctx, repo, current_branch, trunk_branch)

    # Get children branches for navigation decisions
    children = ctx.graphite.get_child_branches(ctx.git, repo.root, current_branch)

    # Safety checks before merge (if --cleanup flag is set)
    current_worktree_path = None
    if cleanup:
        # Store current worktree path for later deletion
        current_worktree_path = Ensure.not_none(
            ctx.git.find_worktree_for_branch(repo.root, current_branch),
            f"Could not find worktree for branch '{current_branch}'",
        )
        # Validate clean working tree (no uncommitted changes)
        check_clean_working_tree(ctx)

    # Merge the PR
    ctx.github.merge_pr(repo.root, pr_number)
    ctx.feedback.success(f"Merged PR #{pr_number} for branch {current_branch}")

    # Resolve navigation target
    target_name, was_created = _resolve_navigation_target(
        ctx,
        repo,
        current_branch,
        children,
        down,
        cleanup,
        script,
        trunk_branch,
        current_worktree_path,
    )

    # Show creation message if worktree was just created
    if was_created and not script:
        ctx.feedback.success(f"Created worktree for {target_name} and moved to it")

    # Handle navigation to root
    if target_name == "root":
        if cleanup and current_worktree_path is not None:
            _activate_root_with_cleanup(ctx, repo, script, current_branch, current_worktree_path)
        else:
            activate_root_repo(ctx, repo, script, "land-branch")

    # Handle navigation to non-root target
    target_wt_path = Ensure.not_none(
        ctx.git.find_worktree_for_branch(repo.root, target_name),
        f"Branch '{target_name}' has no worktree. This should not happen.",
    )

    if cleanup and current_worktree_path is not None:
        _activate_with_cleanup(
            ctx, repo, target_wt_path, script, current_branch, current_worktree_path
        )
    else:
        activate_worktree(ctx, repo, target_wt_path, script, "land-branch")
