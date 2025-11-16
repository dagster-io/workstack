"""Split a stack into individual worktrees per branch."""

from pathlib import Path

import click

from workstack.cli.core import discover_repo_context
from workstack.cli.output import user_output
from workstack.core.context import WorkstackContext
from workstack.core.naming_utils import sanitize_worktree_name
from workstack.core.repo_discovery import ensure_workstacks_dir
from workstack.core.split_utils import SplitPlan, create_split_plan, execute_split_plan

# Helper functions for split command


def _validate_flags(up: bool, down: bool) -> None:
    """Validate that --up and --down are not used together.

    Raises:
        SystemExit: If both flags are set
    """
    if up and down:
        user_output(click.style("❌ Error: Cannot use --up and --down together", fg="red"))
        user_output(
            "Use either --up (split upstack) or --down (split downstack) or neither (full stack)"
        )
        raise SystemExit(1)


def _validate_trunk_branch(trunk_branch: str | None) -> None:
    """Validate trunk branch is available.

    Raises:
        SystemExit: If trunk branch cannot be determined
    """
    if not trunk_branch:
        user_output(click.style("❌ Error: Cannot determine trunk branch", fg="red"))
        user_output("Initialize repository or configure trunk branch")
        raise SystemExit(1)


def _get_stack_branches(
    ctx: WorkstackContext,
    repo_root: Path,
    current_branch: str | None,
    trunk_branch: str,
) -> list[str]:
    """Get the Graphite stack for the current or trunk branch.

    Handles detached HEAD state by falling back to trunk branch stack.

    Returns:
        List of branches in the stack (trunk to leaf)

    Raises:
        SystemExit: If branch is not tracked by Graphite
    """
    if current_branch is None:
        # In detached HEAD state, get the full stack from trunk
        stack_branches = ctx.graphite_ops.get_branch_stack(ctx.git_ops, repo_root, trunk_branch)
        if stack_branches is None:
            user_output(f"Error: Trunk branch '{trunk_branch}' is not tracked by Graphite")
            raise SystemExit(1)
    else:
        # Get current branch's stack
        stack_branches = ctx.graphite_ops.get_branch_stack(ctx.git_ops, repo_root, current_branch)
        if stack_branches is None:
            user_output(f"Error: Branch '{current_branch}' is not tracked by Graphite")
            user_output(
                "Run 'gt repo init' to initialize Graphite, or use 'gt track' to track this branch"
            )
            raise SystemExit(1)

    return stack_branches


def _apply_stack_filter(
    stack_branches: list[str],
    current_branch: str | None,
    up: bool,
    down: bool,
) -> list[str]:
    """Apply --up or --down filters to determine which branches to split.

    Args:
        stack_branches: Full stack from trunk to leaf
        current_branch: Currently checked out branch (None if detached)
        up: If True, only split upstack (current to leaf)
        down: If True, only split downstack (trunk to current)

    Returns:
        Filtered list of branches to split

    Notes:
        - If both up and down are False, returns full stack
        - If current_branch is None, filters have no effect
        - If current_branch is not in stack, returns empty list
    """
    if up and current_branch is not None:
        # Only split upstack (from current to leaf)
        if current_branch in stack_branches:
            current_index = stack_branches.index(current_branch)
            return stack_branches[current_index:]
        else:
            # Current branch not in stack, split nothing
            return []
    elif down and current_branch is not None:
        # Only split downstack (from trunk to current)
        if current_branch in stack_branches:
            current_index = stack_branches.index(current_branch)
            return stack_branches[: current_index + 1]
        else:
            # Current branch not in stack, split nothing
            return []
    else:
        # Split entire stack
        return stack_branches


def _check_uncommitted_changes(
    ctx: WorkstackContext,
    current_worktree: Path,
    force: bool,
    dry_run: bool,
) -> None:
    """Check for uncommitted changes unless --force or --dry-run.

    Raises:
        SystemExit: If uncommitted changes detected
    """
    if not force and not dry_run:
        if ctx.git_ops.has_uncommitted_changes(current_worktree):
            user_output(click.style("❌ Error: Uncommitted changes detected", fg="red", bold=True))
            user_output("\nCommit or stash changes before running split")
            raise SystemExit(1)


def _display_stack_preview(
    stack_to_split: list[str],
    trunk_branch: str,
    current_branch: str | None,
    plan: SplitPlan,
) -> None:
    """Display which branches will be split and their status.

    Shows visual indicators for:
    - Trunk branch (stays in root)
    - Current branch (already checked out)
    - Branches with existing worktrees
    - Branches that will get new worktrees
    """
    user_output("\n" + click.style("Stack to split:", bold=True))
    for b in stack_to_split:
        if b == trunk_branch:
            marker = f" {click.style('←', fg='cyan')} trunk (stays in root)"
            branch_display = click.style(b, fg="cyan")
        elif b == current_branch:
            marker = f" {click.style('←', fg='bright_green')} current (already checked out)"
            branch_display = click.style(b, fg="bright_green", bold=True)
        elif b in plan.existing_worktrees:
            marker = f" {click.style('✓', fg='green')} already has worktree"
            branch_display = click.style(b, fg="green")
        elif b in plan.branches_to_split:
            marker = f" {click.style('→', fg='yellow')} will create worktree"
            branch_display = click.style(b, fg="yellow")
        else:
            marker = ""
            branch_display = click.style(b, fg="white", dim=True)

        user_output(f"  {branch_display}{marker}")


def _display_creation_preview(
    plan: SplitPlan,
    dry_run: bool,
) -> None:
    """Display which worktrees will be created.

    Shows paths for each branch that needs a worktree.
    Returns early if no worktrees need to be created.
    """
    if plan.branches_to_split:
        if dry_run:
            user_output(f"\n{click.style('[DRY RUN] Would create:', fg='yellow', bold=True)}")
        else:
            user_output(f"\n{click.style('Will create:', bold=True)}")

        for branch in plan.branches_to_split:
            worktree_path = plan.target_paths[branch]
            path_text = click.style(str(worktree_path), fg="cyan")
            branch_text = click.style(branch, fg="yellow")
            user_output(f"  - {branch_text} at {path_text}")
    else:
        user_output("\n✅ All branches already have worktrees or are excluded")


def _confirm_split(force: bool, dry_run: bool) -> None:
    """Prompt user for confirmation unless --force or --dry-run.

    Raises:
        SystemExit: If user declines
    """
    if not force and not dry_run:
        user_output("")
        if not click.confirm("Proceed with creating worktrees?"):
            user_output(click.style("⭕ Aborted", fg="yellow"))
            raise SystemExit(1)


def _display_results(
    results: list[tuple[str, Path]],
    dry_run: bool,
) -> None:
    """Display results of split operation.

    Shows created worktrees or dry-run simulation results.
    """
    if results:
        for branch, worktree_path in results:
            path_text = click.style(str(worktree_path), fg="green")
            branch_text = click.style(branch, fg="yellow")
            if dry_run:
                user_output(f"[DRY RUN] Would create worktree for {branch_text} at {path_text}")
            else:
                user_output(f"✅ Created worktree for {branch_text} at {path_text}")

    if dry_run:
        user_output(f"\n{click.style('[DRY RUN] No changes made', fg='yellow')}")
    else:
        user_output(f"\n✅ Split complete: created {len(results)} worktree(s)")


# Main command


@click.command("split")
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what worktrees would be created without executing",
)
@click.option(
    "--up",
    is_flag=True,
    help="Only split upstack (current branch to leaf). Default is entire stack.",
)
@click.option(
    "--down",
    is_flag=True,
    help="Only split downstack (trunk to current branch). Default is entire stack.",
)
@click.pass_obj
def split_cmd(
    ctx: WorkstackContext,
    force: bool,
    dry_run: bool,
    up: bool,
    down: bool,
) -> None:
    """Split a stack into individual worktrees per branch.

    This is the inverse of consolidate - it creates individual worktrees for each
    branch in the stack (except trunk and the current branch).

    By default, splits the full stack (trunk to leaf). With --up or --down, splits
    only a portion of the stack.

    This command is useful after consolidating branches for operations like
    'gt restack', allowing you to return to the ephemeral worktree pattern.

    \b
    Examples:
      # Split full stack into individual worktrees (default)
      $ workstack split

      # Split only upstack (current to leaf)
      $ workstack split --up

      # Split only downstack (trunk to current)
      $ workstack split --down

      # Preview changes without executing
      $ workstack split --dry-run

      # Skip confirmation prompt
      $ workstack split --force

    Notes:
    - Trunk branch (main/master) stays in root worktree
    - Current branch cannot get its own worktree (already checked out)
    - Existing worktrees are preserved (idempotent operation)
    - Creates worktrees in the .workstacks directory
    """
    # 1. Validate input flags
    _validate_flags(up, down)

    # 2. Gather repository context
    current_worktree = ctx.cwd
    current_branch = ctx.git_ops.get_current_branch(current_worktree)
    repo = discover_repo_context(ctx, current_worktree)
    trunk_branch = ctx.trunk_branch
    _validate_trunk_branch(trunk_branch)
    # After validation, trunk_branch is guaranteed to be non-None
    assert trunk_branch is not None  # Type narrowing for mypy/pyright

    # 3. Get stack branches
    stack_branches = _get_stack_branches(ctx, repo.root, current_branch, trunk_branch)

    # 4. Apply stack filters
    stack_to_split = _apply_stack_filter(stack_branches, current_branch, up, down)

    # 5. Safety checks
    _check_uncommitted_changes(ctx, current_worktree, force, dry_run)

    # 6. Create split plan
    all_worktrees = ctx.git_ops.list_worktrees(repo.root)
    workstacks_dir = ensure_workstacks_dir(repo)
    plan = create_split_plan(
        stack_branches=stack_to_split,
        trunk_branch=trunk_branch,
        current_branch=current_branch,
        all_worktrees=all_worktrees,
        workstacks_dir=workstacks_dir,
        sanitize_worktree_name=sanitize_worktree_name,
        source_worktree_path=current_worktree,
        repo_root=repo.root,
    )

    # 7. Display preview
    _display_stack_preview(stack_to_split, trunk_branch, current_branch, plan)
    _display_creation_preview(plan, dry_run)

    # Early exit if nothing to do
    if not plan.branches_to_split:
        return

    # 8. Get user confirmation
    _confirm_split(force, dry_run)

    # 9. Execute or simulate
    user_output("")
    if dry_run:
        results = [(branch, plan.target_paths[branch]) for branch in plan.branches_to_split]
    else:
        results = execute_split_plan(plan, ctx.git_ops)

    # 10. Display results
    _display_results(results, dry_run)
