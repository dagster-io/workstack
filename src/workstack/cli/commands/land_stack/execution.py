"""Core landing sequence execution for land-stack command."""

from collections.abc import Callable
from pathlib import Path

import click

from workstack.cli.commands.land_stack.discovery import _get_all_children
from workstack.cli.commands.land_stack.models import BranchPR
from workstack.cli.commands.land_stack.output import _emit, _format_cli_command, _format_description
from workstack.core.context import WorkstackContext


def _execute_and_emit(
    operation: Callable[[], None],
    cli_command: str,
    *,
    dry_run: bool,
    script_mode: bool,
) -> None:
    """Execute operation (if not dry_run) and emit CLI command.

    Args:
        operation: Operation to execute
        cli_command: CLI command string to display
        dry_run: If True, skip operation execution
        script_mode: True when running in --script mode (output to stderr)
    """
    if not dry_run:
        operation()
    check = click.style("✓", fg="green")
    _emit(_format_cli_command(cli_command, check), script_mode=script_mode)


def _execute_sequence(
    operations: list[tuple[Callable[[], None], str]],
    *,
    dry_run: bool,
    script_mode: bool,
) -> None:
    """Execute sequence of operations and emit corresponding commands.

    Args:
        operations: List of (operation, cli_command) tuples
        dry_run: If True, skip operation execution
        script_mode: True when running in --script mode (output to stderr)
    """
    for operation, cli_cmd in operations:
        _execute_and_emit(operation, cli_cmd, dry_run=dry_run, script_mode=script_mode)


def _execute_checkout_phase(
    ctx: WorkstackContext,
    repo_root: Path,
    branch: str,
    *,
    dry_run: bool,
    script_mode: bool,
) -> None:
    """Execute checkout phase for landing a branch.

    Args:
        ctx: WorkstackContext with access to operations
        repo_root: Repository root directory
        branch: Branch name to checkout
        dry_run: If True, show what would be done without executing
        script_mode: True when running in --script mode (output to stderr)
    """
    # Check if we're already on the target branch (LBYL)
    # This handles the case where we're in a linked worktree on the branch being landed
    current_branch = ctx.git_ops.get_current_branch(Path.cwd())

    if current_branch != branch:
        # Only checkout if we're not already on the branch
        _execute_and_emit(
            lambda: ctx.git_ops.checkout_branch(repo_root, branch),
            f"git checkout {branch}",
            dry_run=dry_run,
            script_mode=script_mode,
        )
    else:
        # Already on branch, display as already done
        check = click.style("✓", fg="green")
        already_msg = f"already on {branch}"
        _emit(_format_description(already_msg, check), script_mode=script_mode)


def _execute_merge_phase(
    ctx: WorkstackContext,
    repo_root: Path,
    pr_number: int,
    *,
    verbose: bool,
    dry_run: bool,
    script_mode: bool,
) -> None:
    """Execute PR merge phase for landing a branch.

    Args:
        ctx: WorkstackContext with access to operations
        repo_root: Repository root directory
        pr_number: PR number to merge
        verbose: If True, show detailed output
        dry_run: If True, show what would be done without executing
        script_mode: True when running in --script mode (output to stderr)
    """
    merge_cmd = f"gh pr merge {pr_number} --squash"

    _execute_and_emit(
        lambda: ctx.github_ops.merge_pr(repo_root, pr_number, squash=True, verbose=verbose),
        merge_cmd,
        dry_run=dry_run,
        script_mode=script_mode,
    )


def _execute_sync_trunk_phase(
    ctx: WorkstackContext,
    repo_root: Path,
    branch: str,
    parent: str,
    *,
    dry_run: bool,
    script_mode: bool,
) -> None:
    """Execute trunk sync phase after PR merge.

    Args:
        ctx: WorkstackContext with access to operations
        repo_root: Repository root directory
        branch: Current branch name
        parent: Parent branch name (should be trunk)
        dry_run: If True, show what would be done without executing
        script_mode: True when running in --script mode (output to stderr)
    """
    # Sync trunk to include just-merged PR commits
    operations = [
        (
            lambda: ctx.git_ops.fetch_branch(repo_root, "origin", parent),
            f"git fetch origin {parent}",
        ),
        (
            lambda: ctx.git_ops.checkout_branch(repo_root, parent),
            f"git checkout {parent}",
        ),
        (
            lambda: ctx.git_ops.pull_branch(repo_root, "origin", parent, ff_only=True),
            f"git pull --ff-only origin {parent}",
        ),
        (
            lambda: ctx.git_ops.checkout_branch(repo_root, branch),
            f"git checkout {branch}",
        ),
    ]
    _execute_sequence(operations, dry_run=dry_run, script_mode=script_mode)


def _execute_restack_phase(
    ctx: WorkstackContext,
    repo_root: Path,
    *,
    verbose: bool,
    dry_run: bool,
    script_mode: bool,
) -> None:
    """Execute restack phase using Graphite sync.

    Args:
        ctx: WorkstackContext with access to operations
        repo_root: Repository root directory
        verbose: If True, show detailed output
        dry_run: If True, show what would be done without executing
        script_mode: True when running in --script mode (output to stderr)
    """
    _execute_and_emit(
        lambda: ctx.graphite_ops.sync(repo_root, force=True, quiet=not verbose),
        "gt sync -f",
        dry_run=dry_run,
        script_mode=script_mode,
    )


def _force_push_upstack_branches(
    ctx: WorkstackContext,
    repo_root: Path,
    branch: str,
    all_branches_metadata: dict,
    *,
    verbose: bool,
    dry_run: bool,
    script_mode: bool,
) -> list[str]:
    """Force-push all upstack branches after restack.

    After gt sync -f rebases remaining branches locally, push them to GitHub
    so subsequent PR merges will succeed.

    Args:
        ctx: WorkstackContext with access to operations
        repo_root: Repository root directory
        branch: Current branch name
        all_branches_metadata: Graphite branch metadata
        verbose: If True, show detailed output
        dry_run: If True, show what would be done without executing
        script_mode: True when running in --script mode (output to stderr)

    Returns:
        List of upstack branch names that were force-pushed
    """
    # Get all children of the current branch recursively
    upstack_branches = _get_all_children(branch, all_branches_metadata)

    for upstack_branch in upstack_branches:
        submit_cmd = f"gt submit --branch {upstack_branch} --no-edit"
        _execute_and_emit(
            lambda b=upstack_branch: ctx.graphite_ops.submit_branch(
                repo_root, b, quiet=not verbose
            ),
            submit_cmd,
            dry_run=dry_run,
            script_mode=script_mode,
        )

    return upstack_branches


def _update_upstack_pr_bases(
    ctx: WorkstackContext,
    repo_root: Path,
    upstack_branches: list[str],
    all_branches_metadata: dict,
    *,
    verbose: bool,
    dry_run: bool,
    script_mode: bool,
) -> None:
    """Update PR base branches on GitHub after force-push.

    After force-pushing rebased commits, update stale PR bases on GitHub.
    This must happen AFTER force-push because GitHub rejects base changes
    when the new base doesn't contain the PR's head commits.

    For each upstack branch that was force-pushed:
    1. Get its updated parent from Graphite metadata
    2. Get its PR number and current base from GitHub
    3. Update base if stale (current base != expected parent)

    Args:
        ctx: WorkstackContext with access to operations
        repo_root: Repository root directory
        upstack_branches: List of upstack branches that were force-pushed
        all_branches_metadata: Graphite branch metadata
        verbose: If True, show detailed output
        dry_run: If True, show what would be done without executing
        script_mode: True when running in --script mode (output to stderr)
    """
    for upstack_branch in upstack_branches:
        # Get updated parent from Graphite metadata (should be correct after sync)
        branch_metadata = all_branches_metadata.get(upstack_branch)
        if branch_metadata is None:
            continue

        expected_parent = branch_metadata.parent
        if expected_parent is None:
            continue

        # Get PR status to check if PR exists and is open
        pr_info = ctx.github_ops.get_pr_status(repo_root, upstack_branch, debug=False)
        if pr_info.state != "OPEN":
            continue

        if pr_info.pr_number is None:
            continue

        pr_number = pr_info.pr_number

        # Check current base on GitHub
        current_base = ctx.github_ops.get_pr_base_branch(repo_root, pr_number)
        if current_base is None:
            continue

        # Update base if stale
        if current_base != expected_parent:
            if verbose or dry_run:
                msg = f"  Updating PR #{pr_number} base: {current_base} → {expected_parent}"
                _emit(msg, script_mode=script_mode)

            edit_cmd = f"gh pr edit {pr_number} --base {expected_parent}"
            _execute_and_emit(
                lambda pr=pr_number, parent=expected_parent: ctx.github_ops.update_pr_base_branch(
                    repo_root, pr, parent
                ),
                edit_cmd,
                dry_run=dry_run,
                script_mode=script_mode,
            )
        elif verbose:
            _emit(
                f"  PR #{pr_number} base already correct: {current_base}",
                script_mode=script_mode,
            )


def land_branch_sequence(
    ctx: WorkstackContext,
    repo_root: Path,
    branches: list[BranchPR],
    *,
    verbose: bool,
    dry_run: bool,
    down_only: bool,
    script_mode: bool,
) -> list[str]:
    """Land branches sequentially, one at a time with restack between each.

    Args:
        ctx: WorkstackContext with access to operations
        repo_root: Repository root directory
        branches: List of BranchPR to land
        verbose: If True, show detailed output
        dry_run: If True, show what would be done without executing
        down_only: If True, skip upstack rebase and force-push operations
        script_mode: True when running in --script mode (output to stderr)

    Returns:
        List of successfully merged branch names

    Raises:
        subprocess.CalledProcessError: If git/gh/gt commands fail
        Exception: If other operations fail
    """
    merged_branches: list[str] = []
    check = click.style("✓", fg="green")

    for _idx, branch_pr in enumerate(branches, 1):
        branch = branch_pr.branch
        pr_number = branch_pr.pr_number

        # Get parent for display and validation
        parent = ctx.graphite_ops.get_parent_branch(ctx.git_ops, repo_root, branch)
        parent_display = parent if parent else "trunk"

        # Print section header
        _emit("", script_mode=script_mode)
        pr_styled = click.style(f"#{pr_number}", fg="cyan")
        branch_styled = click.style(branch, fg="yellow")
        parent_styled = click.style(parent_display, fg="yellow")
        msg = f"Landing PR {pr_styled} ({branch_styled} → {parent_styled})..."
        _emit(msg, script_mode=script_mode)

        # Phase 1: Checkout
        _execute_checkout_phase(ctx, repo_root, branch, dry_run=dry_run, script_mode=script_mode)

        # Phase 2: Verify stack integrity
        all_branches = ctx.graphite_ops.get_all_branches(ctx.git_ops, repo_root)

        # Parent should be trunk after previous restacks
        if parent is None or parent not in all_branches or not all_branches[parent].is_trunk:
            if not dry_run:
                raise RuntimeError(
                    f"Stack integrity broken: {branch} parent is '{parent}', "
                    f"expected trunk branch. Previous restack may have failed."
                )

        # Show specific verification message with branch and expected parent
        trunk_name = parent if parent else "trunk"
        desc = _format_description(f"verify {branch} parent is {trunk_name}", check)
        _emit(desc, script_mode=script_mode)

        # Phase 3: Merge PR
        _execute_merge_phase(
            ctx, repo_root, pr_number, verbose=verbose, dry_run=dry_run, script_mode=script_mode
        )
        merged_branches.append(branch)

        # Phase 3.5: Sync trunk with remote
        # At this point, parent should be trunk (verified in Phase 2)
        if parent is None:
            raise RuntimeError(f"Cannot sync trunk: {branch} has no parent branch")

        _execute_sync_trunk_phase(
            ctx, repo_root, branch, parent, dry_run=dry_run, script_mode=script_mode
        )

        # Phase 4: Restack (skip if down_only)
        if not down_only:
            _execute_restack_phase(
                ctx, repo_root, verbose=verbose, dry_run=dry_run, script_mode=script_mode
            )

            # Phase 5: Force-push rebased branches
            # Get ALL upstack branches from the full Graphite tree, not just
            # the branches in our landing list. After landing feat-1 in a stack
            # like main → feat-1 → feat-2 → feat-3, we need to force-push BOTH
            # feat-2 and feat-3, even if we're only landing up to feat-2.
            all_branches_metadata = ctx.graphite_ops.get_all_branches(ctx.git_ops, repo_root)
            if all_branches_metadata:
                upstack_branches = _force_push_upstack_branches(
                    ctx,
                    repo_root,
                    branch,
                    all_branches_metadata,
                    verbose=verbose,
                    dry_run=dry_run,
                    script_mode=script_mode,
                )

                # Phase 6: Update PR base branches on GitHub after force-push
                if upstack_branches:
                    _update_upstack_pr_bases(
                        ctx,
                        repo_root,
                        upstack_branches,
                        all_branches_metadata,
                        verbose=verbose,
                        dry_run=dry_run,
                        script_mode=script_mode,
                    )

    return merged_branches
