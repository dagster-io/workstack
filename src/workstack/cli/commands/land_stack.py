import subprocess
from pathlib import Path

import click

from workstack.cli.core import discover_repo_context
from workstack.core.action_stream import Action, DryRunStream, ProductionStream
from workstack.core.context import WorkstackContext


def _format_cli_command(cmd: str, check: str) -> str:
    """Format a CLI command operation for display.

    Args:
        cmd: The CLI command string (e.g., "git checkout main")
        check: Checkmark string to append

    Returns:
        Formatted operation string with styling
    """
    cmd_styled = click.style(cmd, fg="white", dim=True)
    return f"  {cmd_styled} {check}"


def _format_description(description: str, check: str) -> str:
    """Format an internal operation description for display.

    Args:
        description: Description text (will be wrapped in brackets)
        check: Checkmark string to append

    Returns:
        Formatted description string with dim styling
    """
    desc_styled = click.style(f"[{description}]", dim=True)
    return f"  {desc_styled} {check}"


def _get_branches_to_land(ctx: WorkstackContext, repo_root: Path, current_branch: str) -> list[str]:
    """Get branches to land from bottom of stack up to and including current branch.

    For PR landing, we need to land from the bottom (closest to trunk) upward,
    as each PR depends on the one below it. This returns all branches from the
    start of the stack up to the current branch.

    Args:
        ctx: WorkstackContext with access to graphite operations
        repo_root: Repository root directory
        current_branch: Name of the current branch

    Returns:
        List of branch names from bottom of stack to current (inclusive, excluding trunk)
        Empty list if branch not in stack
    """
    # Get full stack (trunk to leaves)
    stack = ctx.graphite_ops.get_branch_stack(ctx.git_ops, repo_root, current_branch)
    if stack is None:
        return []

    # Get all branch metadata to filter out trunk branches
    all_branches = ctx.graphite_ops.get_all_branches(ctx.git_ops, repo_root)
    if not all_branches:
        return []

    # Filter stack to exclude trunk branches
    filtered_stack = [b for b in stack if b in all_branches and not all_branches[b].is_trunk]

    # Find current branch index
    if current_branch not in filtered_stack:
        return []

    current_idx = filtered_stack.index(current_branch)

    # Return slice from start to current (inclusive) - bottom to current for PR landing
    return filtered_stack[: current_idx + 1]


def _validate_landing_preconditions(
    ctx: WorkstackContext, repo_root: Path, current_branch: str | None, branches_to_land: list[str]
) -> None:
    """Validate all preconditions for landing are met.

    Args:
        ctx: WorkstackContext with access to operations
        repo_root: Repository root directory
        current_branch: Current branch name (None if detached HEAD)
        branches_to_land: List of branches to land

    Raises:
        SystemExit: If any precondition fails
    """
    # Check Graphite enabled
    use_graphite = ctx.global_config_ops.get_use_graphite()
    if not use_graphite:
        click.echo(
            "Error: 'workstack land-stack' requires Graphite.\n\n"
            "To fix:\n"
            "  • Run: workstack config set use-graphite true\n"
            "  • Install Graphite CLI if needed: brew install withgraphite/tap/graphite",
            err=True,
        )
        raise SystemExit(1)

    # Check not detached HEAD
    if current_branch is None:
        click.echo(
            "Error: HEAD is detached (not on a branch)\n\n"
            "To fix:\n"
            "  • Check out a branch: git checkout <branch-name>",
            err=True,
        )
        raise SystemExit(1)

    # Check no uncommitted changes
    if ctx.git_ops.has_uncommitted_changes(repo_root):
        click.echo(
            "Error: Working directory has uncommitted changes\n"
            "Landing requires a clean working directory.\n\n"
            "To fix:\n"
            "  • Commit your changes: git add . && git commit -m 'message'\n"
            "  • Stash your changes: git stash\n"
            "  • Discard your changes: git reset --hard HEAD",
            err=True,
        )
        raise SystemExit(1)

    # Check current branch not trunk
    all_branches = ctx.graphite_ops.get_all_branches(ctx.git_ops, repo_root)
    if current_branch in all_branches and all_branches[current_branch].is_trunk:
        click.echo(
            f"Error: Cannot land trunk branch '{current_branch}'\n"
            "Trunk branches (main/master) cannot be landed.\n\n"
            "To fix:\n"
            "  • Check out a feature branch: git checkout <feature-branch>",
            err=True,
        )
        raise SystemExit(1)

    # Validate stack exists
    if not branches_to_land:
        stack = ctx.graphite_ops.get_branch_stack(ctx.git_ops, repo_root, current_branch)
        if stack is None:
            click.echo(
                f"Error: Branch '{current_branch}' is not tracked by Graphite\n\n"
                "To fix:\n"
                "  • Track the branch with Graphite: gt create -s\n"
                "  • Or switch to a Graphite-tracked branch",
                err=True,
            )
        else:
            click.echo(
                f"Error: No branches to land\n"
                f"Branch '{current_branch}' may already be landed or is a trunk branch.",
                err=True,
            )
        raise SystemExit(1)

    # Check no branches in stack are checked out in other worktrees
    current_worktree = Path.cwd().resolve()
    worktree_conflicts: list[tuple[str, Path]] = []

    for branch in branches_to_land:
        worktree_path = ctx.git_ops.is_branch_checked_out(repo_root, branch)
        if worktree_path and worktree_path.resolve() != current_worktree:
            worktree_conflicts.append((branch, worktree_path))

    if worktree_conflicts:
        click.echo(
            "Error: Cannot land stack - branches are checked out in multiple worktrees\n\n"
            "The following branches are checked out in other worktrees:",
            err=True,
        )
        for branch, path in worktree_conflicts:
            branch_styled = click.style(branch, fg="yellow")
            path_styled = click.style(str(path), fg="white", dim=True)
            click.echo(f"  • {branch_styled} → {path_styled}", err=True)

        click.echo(
            "\nGit does not allow checking out a branch that is already checked out\n"
            "in another worktree. To land this stack, you need to consolidate all\n"
            "branches into the current worktree first.\n\n"
            "To fix:\n"
            "  • Run: workstack consolidate\n"
            "  • This will remove other worktrees for branches in this stack\n"
            "  • Then retry: workstack land-stack",
            err=True,
        )
        raise SystemExit(1)


def _validate_branches_have_prs(
    ctx: WorkstackContext, repo_root: Path, branches: list[str]
) -> list[tuple[str, int, str]]:
    """Validate all branches have open PRs.

    Args:
        ctx: WorkstackContext with access to GitHub operations
        repo_root: Repository root directory
        branches: List of branch names to validate

    Returns:
        List of tuples (branch, pr_number, title) for all valid branches

    Raises:
        SystemExit: If any branch has invalid PR state
    """
    errors: list[str] = []
    valid_branches: list[tuple[str, int, str]] = []

    for branch in branches:
        state, pr_number, title = ctx.github_ops.get_pr_status(repo_root, branch, debug=False)

        if state == "NONE":
            errors.append(f"No PR found for branch '{branch}'")
        elif state == "MERGED":
            errors.append(f"PR #{pr_number} for '{branch}' is already merged")
        elif state == "CLOSED":
            errors.append(f"PR #{pr_number} for '{branch}' is closed")
        elif state == "OPEN" and pr_number is not None and title is not None:
            valid_branches.append((branch, pr_number, title))
        else:
            errors.append(f"Unexpected PR state for '{branch}': {state}")

    if errors:
        click.echo("Error: Cannot land stack\n\nThe following branches have issues:", err=True)
        for error in errors:
            click.echo(f"  • {error}", err=True)
        raise SystemExit(1)

    return valid_branches


def _show_landing_plan(
    current_branch: str,
    trunk_branch: str,
    branches: list[tuple[str, int, str]],
    *,
    force: bool,
    dry_run: bool,
) -> None:
    """Display landing plan and get user confirmation.

    Args:
        current_branch: Name of current branch
        trunk_branch: Name of trunk branch (displayed at bottom)
        branches: List of (branch, pr_number, title) tuples to land (bottom to top order)
        force: If True, skip confirmation
        dry_run: If True, skip confirmation and add dry-run prefix

    Raises:
        SystemExit: If user declines confirmation
    """
    # Display header
    header = "📋 Summary"
    if dry_run:
        header += click.style(" (dry run)", fg="bright_black")
    click.echo(click.style(f"\n{header}", bold=True))
    click.echo()

    # Display summary
    pr_text = "PR" if len(branches) == 1 else "PRs"
    click.echo(f"Landing {len(branches)} {pr_text}:")

    # Display PRs in format: #PR (branch → target) - title
    # Show in landing order (bottom to top)
    for branch, pr_number, title in branches:
        pr_styled = click.style(f"#{pr_number}", fg="cyan")
        branch_styled = click.style(branch, fg="yellow")
        trunk_styled = click.style(trunk_branch, fg="yellow")
        title_styled = click.style(title, fg="bright_magenta")

        line = f"  {pr_styled} ({branch_styled} → {trunk_styled}) - {title_styled}"
        click.echo(line)

    click.echo()

    # Confirmation or force flag
    if dry_run:
        # No additional message needed - already indicated in header
        pass
    elif force:
        click.echo("[--force flag set, proceeding without confirmation]")
    else:
        if not click.confirm("Proceed with landing these PRs?", default=False):
            click.echo("Landing cancelled.")
            raise SystemExit(0)


def _land_branch_sequence(
    ctx: WorkstackContext,
    repo_root: Path,
    branches: list[tuple[str, int, str]],
    *,
    verbose: bool,
    dry_run: bool,
) -> tuple[list[str], str | None, list[str]]:
    """Land branches sequentially, one at a time with restack between each.

    Args:
        ctx: WorkstackContext with access to operations
        repo_root: Repository root directory
        branches: List of (branch, pr_number, title) tuples to land
        verbose: If True, show detailed output
        dry_run: If True, show what would be done without executing

    Returns:
        Tuple of (merged_branches, failure_reason, operations)
        - merged_branches: List of successfully merged branch names
        - failure_reason: Error message if landing failed, None if all succeeded
        - operations: List of formatted operation strings for display
    """
    merged_branches: list[str] = []
    operations: list[str] = []
    stream = DryRunStream(ctx, verbose) if dry_run else ProductionStream(ctx, verbose)

    check = click.style("✓", fg="green")

    for _idx, (branch, pr_number, _title) in enumerate(branches, 1):
        # Phase 1: Checkout
        try:
            stream.execute(Action.git_checkout(ctx, repo_root, branch))
            operations.append(_format_cli_command(f"git checkout {branch}", check))
        except Exception as e:
            return merged_branches, f"Failed to checkout {branch}: {e}", operations

        # Phase 2: Verify stack integrity
        parent = ctx.graphite_ops.get_parent_branch(ctx.git_ops, repo_root, branch)
        all_branches = ctx.graphite_ops.get_all_branches(ctx.git_ops, repo_root)

        # Parent should be trunk after previous restacks
        is_parent_trunk = (
            parent is not None and parent in all_branches and all_branches[parent].is_trunk
        )
        if not is_parent_trunk:
            return (
                merged_branches,
                f"Stack integrity broken: {branch} parent is '{parent}', "
                f"expected trunk branch. Previous restack may have failed.",
                operations,
            )

        # Show specific verification message with branch and expected parent
        trunk_name = parent if parent else "trunk"
        operations.append(_format_description(f"verify {branch} parent is {trunk_name}", check))

        # Phase 3: Merge PR
        try:
            stream.execute(
                Action.subprocess_run(
                    f"gh pr merge {pr_number} --squash --auto",
                    ["gh", "pr", "merge", str(pr_number), "--squash", "--auto"],
                    repo_root,
                )
            )
            merge_cmd = f"gh pr merge {pr_number} --squash --auto"
            operations.append(_format_cli_command(merge_cmd, check))
            merged_branches.append(branch)

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            msg = f"Failed to merge PR #{pr_number} for {branch}: {error_msg}"
            return merged_branches, msg, operations
        except FileNotFoundError:
            return (
                merged_branches,
                "gh command not found. Install GitHub CLI: brew install gh",
                operations,
            )

        # Phase 4: Restack
        try:
            stream.execute(Action.graphite_sync(ctx, repo_root, force=True, quiet=not verbose))
            operations.append(_format_cli_command("gt sync -f", check))
        except Exception as e:
            return merged_branches, f"Failed to restack after merging {branch}: {e}", operations

    return merged_branches, None, operations


def _cleanup_and_navigate(
    ctx: WorkstackContext,
    repo_root: Path,
    merged_branches: list[str],
    *,
    verbose: bool,
    dry_run: bool,
) -> tuple[list[str], str]:
    """Clean up merged worktrees and navigate to appropriate branch.

    Args:
        ctx: WorkstackContext with access to operations
        repo_root: Repository root directory
        merged_branches: List of successfully merged branch names
        verbose: If True, show detailed output
        dry_run: If True, show what would be done without executing

    Returns:
        Tuple of (operations, final_branch)
        - operations: List of formatted operation strings for display
        - final_branch: Name of branch after cleanup and navigation
    """
    operations: list[str] = []
    check = click.style("✓", fg="green")
    stream = DryRunStream(ctx, verbose) if dry_run else ProductionStream(ctx, verbose)

    # Get last merged branch to find next unmerged child
    last_merged = merged_branches[-1] if merged_branches else None

    # Step 1: Checkout main
    stream.execute(Action.git_checkout(ctx, repo_root, "main"))
    operations.append(_format_cli_command("git checkout main", check))
    final_branch = "main"

    # Step 2: Sync worktrees
    base_cmd = "workstack sync -f"
    if verbose:
        base_cmd += " --verbose"

    try:
        cmd = ["workstack", "sync", "-f"]
        if verbose:
            cmd.append("--verbose")

        stream.execute(Action.subprocess_run(base_cmd, cmd, repo_root))
        operations.append(_format_cli_command(base_cmd, check))
    except subprocess.CalledProcessError as e:
        click.echo(f"Warning: Cleanup sync failed: {e}", err=True)

    # Step 3: Navigate to next branch or stay on main
    # Check if last merged branch had unmerged children
    if last_merged:
        all_branches = ctx.graphite_ops.get_all_branches(ctx.git_ops, repo_root)
        if last_merged in all_branches:
            children = all_branches[last_merged].children or []
            # Check if any children still exist and are unmerged
            for child in children:
                if child in all_branches:
                    try:
                        stream.execute(Action.git_checkout(ctx, repo_root, child))
                        operations.append(_format_cli_command(f"git checkout {child}", check))
                        final_branch = child
                        return operations, final_branch
                    except Exception:
                        # Child branch may have been deleted - continue to next
                        # child or fall through
                        pass

    # No unmerged children, stay on main (already checked out above)
    return operations, final_branch


def _show_final_state(
    merged_branches: list[str],
    final_branch: str,
    *,
    dry_run: bool,
) -> None:
    """Display final state after landing operations.

    Args:
        merged_branches: List of successfully merged branch names
        final_branch: Name of current branch after all operations
        dry_run: If True, this was a dry run
    """
    click.echo("Final state:")
    click.echo()

    # Success message
    pr_text = "PR" if len(merged_branches) == 1 else "PRs"
    success_msg = f"✅ Successfully landed {len(merged_branches)} {pr_text}"
    if dry_run:
        success_msg += click.style(" (dry run)", fg="bright_black")
    click.echo(f"  {success_msg}")

    # Current branch
    branch_styled = click.style(final_branch, fg="yellow")
    click.echo(f"  Current branch: {branch_styled}")

    # Merged branches
    branches_list = ", ".join(click.style(b, fg="yellow") for b in merged_branches)
    click.echo(f"  Merged branches: {branches_list}")

    # Worktrees status
    click.echo("  Worktrees: cleaned up")


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
@click.pass_obj
def land_stack(ctx: WorkstackContext, force: bool, verbose: bool, dry_run: bool) -> None:
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
    repo = discover_repo_context(ctx, Path.cwd())

    # Get current branch
    current_branch = ctx.git_ops.get_current_branch(Path.cwd())

    # Get branches to land
    branches_to_land = _get_branches_to_land(ctx, repo.root, current_branch or "")

    # Validate preconditions
    _validate_landing_preconditions(ctx, repo.root, current_branch, branches_to_land)

    # Validate all branches have open PRs
    valid_branches = _validate_branches_have_prs(ctx, repo.root, branches_to_land)

    # Get trunk branch (parent of first branch to land)
    if not valid_branches:
        click.echo("No branches to land.", err=True)
        raise SystemExit(1)

    first_branch = valid_branches[0][0]  # First tuple is (branch, pr_number, title)
    trunk_branch = ctx.graphite_ops.get_parent_branch(ctx.git_ops, repo.root, first_branch)
    if trunk_branch is None:
        click.echo(f"Error: Could not determine trunk branch for {first_branch}", err=True)
        raise SystemExit(1)

    # Show plan and get confirmation
    _show_landing_plan(
        current_branch or "", trunk_branch, valid_branches, force=force, dry_run=dry_run
    )

    # Execute landing sequence
    merged_branches, failure_reason, landing_operations = _land_branch_sequence(
        ctx, repo.root, valid_branches, verbose=verbose, dry_run=dry_run
    )

    # Report results if failure
    if failure_reason:
        # Show operations executed before failure
        if landing_operations:
            click.echo()
            click.echo(click.style("Operations executed:", bold=True))
            click.echo()
            for op in landing_operations:
                click.echo(op)
            click.echo()

        error_msg = click.style(f"❌ Landing stopped: {failure_reason}", fg="red")
        click.echo(error_msg, err=True)
        if merged_branches:
            branches_styled = ", ".join(click.style(b, fg="yellow") for b in merged_branches)
            click.echo(f"\nSuccessfully merged before failure: {branches_styled}")
        raise SystemExit(1)

    # All succeeded - collect cleanup operations
    cleanup_operations, final_branch = _cleanup_and_navigate(
        ctx, repo.root, merged_branches, verbose=verbose, dry_run=dry_run
    )

    # Show all operations (landing + cleanup)
    all_operations = landing_operations + cleanup_operations
    click.echo(click.style("Operations executed:", bold=True))
    click.echo()
    for op in all_operations:
        click.echo(op)

    # Show final state
    click.echo()
    _show_final_state(merged_branches, final_branch, dry_run=dry_run)
