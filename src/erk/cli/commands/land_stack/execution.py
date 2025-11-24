"""Core landing sequence execution for land-stack command."""

from pathlib import Path

import click

from erk.cli.commands.land_stack.discovery import _get_all_children
from erk.cli.commands.land_stack.models import BranchPR
from erk.cli.commands.land_stack.output import _emit, _format_description
from erk.cli.commands.land_stack.retry import retry_with_backoff
from erk.core.context import ErkContext
from erk_shared.git.abc import find_worktree_for_branch


class MergeabilityUnknownError(Exception):
    """Raised when PR mergeability status is UNKNOWN and needs retry.

    This exception triggers the @retry_with_backoff decorator to retry
    the mergeability check, giving GitHub time to recalculate merge status
    after PR base updates.
    """

    def __init__(self, pr_number: int, attempt: int):
        self.pr_number = pr_number
        self.attempt = attempt
        super().__init__(
            f"PR #{pr_number} mergeability status is UNKNOWN (attempt {attempt}). "
            "GitHub may still be recalculating after base update."
        )


@retry_with_backoff(max_attempts=5, base_delay=2.0, backoff_factor=2.0)
def _check_pr_mergeable_with_retry(
    ctx: ErkContext,
    repo_root: Path,
    pr_number: int,
) -> tuple[bool, str, str | None]:
    """Check if PR is mergeable with retry and backoff.

    Queries GitHub for PR mergeability status and maps the status to user-friendly
    messages. Uses retry with backoff to handle GitHub's asynchronous merge status
    recalculation after PR base updates.

    Args:
        ctx: ErkContext with access to operations
        repo_root: Repository root directory
        pr_number: PR number to check

    Returns:
        Tuple of (is_mergeable, status, reason):
        - is_mergeable: True if PR can be merged, False otherwise
        - status: Raw mergeStateStatus from GitHub
        - reason: User-friendly message explaining why PR is not mergeable (None if mergeable)

    Raises:
        RuntimeError: If mergeability check fails after retries
    """
    mergeability = ctx.github.get_pr_mergeability(repo_root, pr_number)

    if mergeability is None:
        msg = f"Failed to check mergeability for PR #{pr_number}"
        raise RuntimeError(msg)

    # Map mergeStateStatus to user-friendly messages
    status = mergeability.merge_state_status

    if status == "CLEAN":
        return (True, status, None)

    if status == "DIRTY":
        return (
            False,
            status,
            "PR has merge conflicts that must be resolved manually",
        )

    if status == "BLOCKED":
        return (
            False,
            status,
            "PR is blocked by branch protection rules",
        )

    if status == "BEHIND":
        return (
            False,
            status,
            "PR branch is behind base and needs updating",
        )

    if status == "UNSTABLE":
        return (
            False,
            status,
            "PR has failing status checks",
        )

    # Handle UNKNOWN status by raising exception to trigger retry
    if status == "UNKNOWN":
        # Note: retry decorator will catch this and retry with backoff
        raise MergeabilityUnknownError(pr_number, attempt=1)  # attempt tracked by decorator

    # Unknown or other status
    return (False, status, f"PR is not in a mergeable state (status: {status})")


def _execute_checkout_phase(
    ctx: ErkContext,
    repo_root: Path,
    branch: str,
    *,
    script_mode: bool,
) -> None:
    """Execute checkout phase for landing a branch.

    Args:
        ctx: ErkContext with access to operations
        repo_root: Repository root directory
        branch: Branch name to checkout
        script_mode: True when running in --script mode (output to stderr)
    """
    # Check if we're already on the target branch (LBYL)
    # This handles the case where we're in a linked worktree on the branch being landed
    current_branch = ctx.git.get_current_branch(ctx.cwd)

    if current_branch != branch:
        # Check if branch is already checked out in any worktree
        # If so, we can't checkout in repo root (git will fail with "already checked out" error)
        checked_out_path = ctx.git.is_branch_checked_out(repo_root, branch)
        if checked_out_path:
            # Branch is checked out elsewhere - skip checkout
            # This is fine because we'll work with it in its current worktree
            pass
        else:
            # Only checkout if we're not already on the branch and it's not checked out elsewhere
            ctx.git.checkout_branch(repo_root, branch)
    else:
        # Already on branch, display as already done
        check = click.style("✓", fg="green")
        already_msg = f"already on {branch}"
        _emit(_format_description(already_msg, check), script_mode=script_mode)


def _verify_and_update_pr_base(
    ctx: ErkContext,
    repo_root: Path,
    branch: str,
    expected_parent: str,
    pr_number: int,
    *,
    verbose: bool,
    script_mode: bool,
) -> None:
    """Verify PR base matches expected parent, update if stale.

    [CRITICAL: Must be called BEFORE merge to prevent orphaned commits]

    This function implements Phase 2.5 of the landing sequence. It verifies that
    the PR's base branch on GitHub matches the expected parent (typically trunk
    after previous iteration's restack). If the base is stale (e.g., points to
    a deleted parent branch), it updates the base to the expected parent BEFORE
    attempting to merge.

    This prevents the race condition where:
    1. Parent PR merges and deletes its branch (e.g., feat-1)
    2. Child PR's base on GitHub still points to deleted branch
    3. Child PR merges into deleted branch, creating orphaned commit

    Args:
        ctx: ErkContext with access to operations
        repo_root: Repository root directory
        branch: Current branch name
        expected_parent: Expected base branch (should be trunk after restack)
        pr_number: PR number to verify
        verbose: If True, show detailed output
        script_mode: True when running in --script mode

    Raises:
        RuntimeError: If PR base retrieval or update fails after retries
    """
    check = click.style("✓", fg="green")

    # Get current PR base from GitHub (with retry for transient failures)
    @retry_with_backoff(max_attempts=3, base_delay=1.0, ctx=ctx)
    def get_pr_base_with_retry() -> str | None:
        return ctx.github.get_pr_base_branch(repo_root, pr_number)

    current_base = get_pr_base_with_retry()

    # Check if base retrieval failed
    if current_base is None:
        msg = f"Failed to get PR #{pr_number} base from GitHub"
        raise RuntimeError(msg)

    # Check if base matches expected parent
    if current_base != expected_parent:
        # Base is stale - update it
        if verbose:
            msg = f"  PR #{pr_number} base stale: {current_base} → {expected_parent}"
            _emit(msg, script_mode=script_mode)

        # Update PR base (with retry for transient failures)
        @retry_with_backoff(max_attempts=3, base_delay=1.0, ctx=ctx)
        def update_pr_base_with_retry() -> None:
            ctx.github.update_pr_base_branch(repo_root, pr_number, expected_parent)

        update_pr_base_with_retry()

        # Wait for GitHub to recalculate merge status after base update
        ctx.time.sleep(2.0)

        # Show completion message
        desc = _format_description(f"update PR #{pr_number} base to {expected_parent}", check)
        _emit(desc, script_mode=script_mode)
    else:
        # Base is already correct
        if verbose:
            msg = f"  PR #{pr_number} base already correct: {current_base}"
            _emit(msg, script_mode=script_mode)
        else:
            # Show concise verification message
            desc = _format_description(f"verify PR #{pr_number} base is {expected_parent}", check)
            _emit(desc, script_mode=script_mode)


def _execute_merge_phase(
    ctx: ErkContext,
    repo_root: Path,
    pr_number: int,
    *,
    verbose: bool,
    script_mode: bool,
) -> None:
    """Execute PR merge phase for landing a branch.

    Args:
        ctx: ErkContext with access to operations
        repo_root: Repository root directory
        pr_number: PR number to merge
        verbose: If True, show detailed output
        script_mode: True when running in --script mode (output to stderr)
    """
    ctx.github.merge_pr(repo_root, pr_number, squash=True, verbose=verbose)


def _execute_sync_trunk_phase(
    ctx: ErkContext,
    repo_root: Path,
    parent: str,
    *,
    script_mode: bool,
) -> None:
    """Execute trunk sync phase after PR merge.

    Syncs trunk branch with remote after a PR merge. If trunk is checked
    out in a worktree, pulls there. Otherwise, checks out and pulls at
    repo_root, leaving repo_root on trunk.

    The repo_root worktree will remain on trunk (parent) after this operation.
    Feature branches are never checked out by this function.

    Args:
        ctx: ErkContext with access to operations
        repo_root: Repository root directory
        parent: Parent branch name (should be trunk)
        script_mode: True when running in --script mode (output to stderr)
    """
    # Sync trunk to include just-merged PR commits
    # Pull in the correct worktree location if branch is checked out elsewhere

    # Fetch parent branch
    ctx.git.fetch_branch(repo_root, "origin", parent)

    # Check if parent is checked out in a worktree
    parent_worktree = ctx.git.find_worktree_for_branch(repo_root, parent)
    if parent_worktree is not None:
        # Parent is in a worktree - pull there
        ctx.git.pull_branch(parent_worktree, "origin", parent, ff_only=True)
    else:
        # Parent is not checked out - safe to checkout in repo_root
        ctx.git.checkout_branch(repo_root, parent)
        ctx.git.pull_branch(repo_root, "origin", parent, ff_only=True)


def _execute_restack_phase(
    ctx: ErkContext,
    repo_root: Path,
    *,
    verbose: bool,
    script_mode: bool,
) -> None:
    """Execute restack phase using Graphite restack.

    Runs `gt restack --no-interactive` to:
    1. Update Graphite metadata about merged branches
    2. Rebase remaining upstack branches onto new trunk state

    This is necessary before submitting upstack branches, otherwise
    gt submit will fail with "merged commits are not contained in trunk".

    Uses gt restack instead of gt sync because:
    - Only affects current stack (surgical approach)
    - Works in non-interactive mode without prompts
    - Safer than gt sync -f which affects all branches

    The --down flag can be used to skip restacking if manual control is desired.

    Args:
        ctx: ErkContext with access to operations
        repo_root: Repository root directory
        verbose: If True, show detailed output
        script_mode: True when running in --script mode (output to stderr)
    """
    ctx.graphite.restack(repo_root, no_interactive=True, quiet=not verbose)


def _force_push_upstack_branches(
    ctx: ErkContext,
    repo_root: Path,
    branch: str,
    all_branches_metadata: dict,
    *,
    verbose: bool,
    script_mode: bool,
) -> list[str]:
    """Force-push all upstack branches after restack.

    After gt restack rebases remaining branches locally, push them to GitHub
    so subsequent PR merges will succeed.

    Args:
        ctx: ErkContext with access to operations
        repo_root: Repository root directory
        branch: Current branch name
        all_branches_metadata: Graphite branch metadata
        verbose: If True, show detailed output
        script_mode: True when running in --script mode (output to stderr)

    Returns:
        List of upstack branch names that were force-pushed
    """
    # Get all children of the current branch recursively
    upstack_branches = _get_all_children(branch, all_branches_metadata)

    # Get list of worktrees to check branch locations (LBYL)
    worktrees = ctx.git.list_worktrees(repo_root)

    for upstack_branch in upstack_branches:
        # Check if branch is checked out in a worktree
        worktree_path = find_worktree_for_branch(worktrees, upstack_branch)

        # If branch is in a worktree, run from there; otherwise use repo_root
        if worktree_path is not None:
            ctx.graphite.submit_branch(worktree_path, upstack_branch, quiet=not verbose)
        else:
            ctx.graphite.submit_branch(repo_root, upstack_branch, quiet=not verbose)

    return upstack_branches


def _update_upstack_pr_bases(
    ctx: ErkContext,
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
        ctx: ErkContext with access to operations
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
        pr_info = ctx.github.get_pr_status(repo_root, upstack_branch, debug=False)
        if pr_info.state != "OPEN":
            continue

        if pr_info.pr_number is None:
            continue

        pr_number = pr_info.pr_number

        # Check current base on GitHub
        current_base = ctx.github.get_pr_base_branch(repo_root, pr_number)
        if current_base is None:
            continue

        # Update base if stale
        if current_base != expected_parent:
            if verbose:
                msg = f"  Updating PR #{pr_number} base: {current_base} → {expected_parent}"
                _emit(msg, script_mode=script_mode)

            ctx.github.update_pr_base_branch(repo_root, pr_number, expected_parent)
        elif verbose:
            _emit(
                f"  PR #{pr_number} base already correct: {current_base}",
                script_mode=script_mode,
            )


def land_branch_sequence(
    ctx: ErkContext,
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
        ctx: ErkContext with access to operations
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
        parent = ctx.graphite.get_parent_branch(ctx.git, repo_root, branch)
        parent_display = parent if parent else "trunk"

        # Print section header
        _emit("", script_mode=script_mode)
        pr_styled = click.style(f"#{pr_number}", fg="cyan")
        branch_styled = click.style(branch, fg="yellow")
        parent_styled = click.style(parent_display, fg="yellow")
        msg = f"Landing PR {pr_styled} ({branch_styled} → {parent_styled})..."
        _emit(msg, script_mode=script_mode)

        # Phase 1: Checkout
        _execute_checkout_phase(ctx, repo_root, branch, script_mode=script_mode)

        # Phase 2: Verify stack integrity
        all_branches = ctx.graphite.get_all_branches(ctx.git, repo_root)

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

        # Phase 2.5: Verify and update PR base [CRITICAL]
        # This phase must run BEFORE merge to prevent race condition where:
        # - Parent PR merges and deletes its branch
        # - Child PR's base on GitHub is stale (still points to deleted parent)
        # - Child PR merges into deleted branch, creating orphaned commit
        #
        # Only verify/update if parent is known (verified in Phase 2)
        if parent is not None:
            _verify_and_update_pr_base(
                ctx,
                repo_root,
                branch,
                parent,  # expected_parent (trunk after restack)
                pr_number,
                verbose=verbose,
                script_mode=script_mode,
            )

        # Phase 2.75: Check PR mergeability before attempting merge
        is_mergeable, status, reason = _check_pr_mergeable_with_retry(ctx, repo_root, pr_number)
        if not is_mergeable:
            error_msg = f"Cannot merge PR #{pr_number}: {reason or status}\n\n"
            error_msg += "Suggested action:\n"
            error_msg += f"1. View PR: gh pr view {pr_number}\n"
            error_msg += "2. Resolve the issue (conflicts, protections, etc.)\n"
            error_msg += "3. Retry landing: erk land-stack"
            raise RuntimeError(error_msg)

        # Show success check for mergeability
        desc = _format_description(f"verify PR #{pr_number} is mergeable", check)
        _emit(desc, script_mode=script_mode)

        # Phase 3: Merge PR
        _execute_merge_phase(ctx, repo_root, pr_number, verbose=verbose, script_mode=script_mode)
        merged_branches.append(branch)

        # Phase 3.5: Sync trunk with remote
        # At this point, parent should be trunk (verified in Phase 2)
        if parent is None:
            raise RuntimeError(f"Cannot sync trunk: {branch} has no parent branch")

        _execute_sync_trunk_phase(ctx, repo_root, parent, script_mode=script_mode)

        # Phase 4: Restack (skip if down_only)
        if not down_only:
            _execute_restack_phase(ctx, repo_root, verbose=verbose, script_mode=script_mode)

            # Phase 5: Force-push rebased branches
            # Get ALL upstack branches from the full Graphite tree, not just
            # the branches in our landing list. After landing feat-1 in a stack
            # like main → feat-1 → feat-2 → feat-3, we need to force-push BOTH
            # feat-2 and feat-3, even if we're only landing up to feat-2.
            all_branches_metadata = ctx.graphite.get_all_branches(ctx.git, repo_root)
            if all_branches_metadata:
                upstack_branches = _force_push_upstack_branches(
                    ctx,
                    repo_root,
                    branch,
                    all_branches_metadata,
                    verbose=verbose,
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
