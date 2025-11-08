"""Consolidate worktrees by removing others containing branches from current stack."""

from pathlib import Path

import click

from workstack.cli.core import discover_repo_context
from workstack.core.context import WorkstackContext


def _get_non_trunk_branches(ctx: WorkstackContext, repo_root: Path, stack: list[str]) -> list[str]:
    """Filter out trunk branches from a stack using GraphiteOps abstraction.

    Raises:
        ValueError: If Graphite cache is missing or cannot be read
    """
    # Get all branches from GraphiteOps abstraction
    all_branches = ctx.graphite_ops.get_all_branches(ctx.git_ops, repo_root)
    if not all_branches:
        raise ValueError("Graphite cache not available")

    # Filter stack to only non-trunk branches
    return [b for b in stack if b in all_branches and not all_branches[b].is_trunk]


@click.command("consolidate")
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be removed without executing",
)
@click.pass_obj
def consolidate_cmd(ctx: WorkstackContext, force: bool, dry_run: bool) -> None:
    """Remove worktrees containing branches from current Graphite stack.

    This command helps consolidate work by removing other worktrees that contain
    branches from your current Graphite stack. This is useful before running
    stack-wide operations like 'gt restack' that require branches to be checked
    out in only one worktree.

    The command will:
    1. Get the current branch's Graphite stack
    2. Find all other worktrees containing branches from that stack
    3. Check for uncommitted changes in worktrees containing stack branches
    4. Remove the identified worktrees (preserving the current one)

    Safety checks:
    - Aborts if any worktree in the stack has uncommitted changes
    - Preserves the current worktree
    - Shows preview before removal (unless --force)

    Examples:

        \b
        # Preview what would be removed
        workstack consolidate --dry-run

        \b
        # Remove with confirmation prompt
        workstack consolidate

        \b
        # Remove without confirmation
        workstack consolidate --force
    """
    # Get current worktree and branch
    current_worktree = Path.cwd()
    current_branch = ctx.git_ops.get_current_branch(current_worktree)

    if current_branch is None:
        click.echo("Error: Current worktree is in detached HEAD state", err=True)
        click.echo("Checkout a branch before running consolidate", err=True)
        raise SystemExit(1)

    # Get repository root
    repo = discover_repo_context(ctx, current_worktree)

    # Get current branch's stack
    stack_branches = ctx.graphite_ops.get_branch_stack(ctx.git_ops, repo.root, current_branch)
    if stack_branches is None:
        click.echo(
            f"Error: Branch '{current_branch}' is not tracked by Graphite",
            err=True,
        )
        click.echo(
            "Run 'gt repo init' to initialize Graphite, or use 'gt track' to track this branch",
            err=True,
        )
        raise SystemExit(1)

    # Get all worktrees
    all_worktrees = ctx.git_ops.list_worktrees(repo.root)

    # Check worktrees in stack for uncommitted changes (including current)
    worktrees_with_changes: list[Path] = []
    for wt in all_worktrees:
        if wt.branch not in stack_branches:
            continue
        if wt.path.exists() and ctx.git_ops.has_uncommitted_changes(wt.path):
            worktrees_with_changes.append(wt.path)

    if worktrees_with_changes:
        click.echo(
            click.style("Error: Uncommitted changes detected in worktrees:", fg="red", bold=True),
            err=True,
        )
        for wt_path in worktrees_with_changes:
            click.echo(f"  - {wt_path}", err=True)
        click.echo("\nCommit or stash changes before running consolidate", err=True)
        raise SystemExit(1)

    # Safety check passed - all worktrees are clean
    click.echo(
        click.style("✅ Safety check: All worktrees have no uncommitted changes", fg="green")
    )
    click.echo()

    # Filter out trunk branches from the stack
    non_trunk_stack_branches = _get_non_trunk_branches(ctx, repo.root, stack_branches)

    # Identify worktrees to remove (branch in stack AND not trunk AND not current worktree)
    # Resolve current_worktree for comparison
    current_worktree_resolved = current_worktree.resolve()
    worktrees_to_remove = [
        wt
        for wt in all_worktrees
        if wt.branch in non_trunk_stack_branches and wt.path.resolve() != current_worktree_resolved
    ]

    # Display preview
    if not worktrees_to_remove:
        click.echo("No other worktrees found containing branches from current stack")
        click.echo(f"\nCurrent stack branches: {', '.join(stack_branches)}")
        return

    click.echo(click.style("📋 Current Stack:", bold=True))
    for branch in stack_branches:
        branch_marker = " (current)" if branch == current_branch else ""
        click.echo(f"  - {click.style(branch, fg='cyan')}{branch_marker}")

    click.echo(f"\n{click.style('🗑️  Safe to remove (no uncommitted changes):', bold=True)}")
    for wt in worktrees_to_remove:
        branch_text = click.style(wt.branch or "detached", fg="yellow")
        path_text = click.style(str(wt.path), fg="cyan")
        click.echo(f"  - {branch_text} at {path_text}")

    # Inform user about stack restackability
    click.echo()
    click.echo(
        f"ℹ️  Note: Use 'gt restack' on {current_worktree_resolved} to restack. "
        "All branches are preserved."
    )

    # Exit if dry-run
    if dry_run:
        click.echo(f"\n{click.style('[DRY RUN] No changes made', fg='yellow', bold=True)}")
        return

    # Get confirmation unless --force
    if not force:
        click.echo()
        if not click.confirm(
            click.style("All worktrees are clean. Proceed with removal?", fg="yellow", bold=True),
            default=False,
        ):
            click.echo(click.style("⭕ Aborted", fg="red", bold=True))
            return

    # Remove worktrees
    click.echo()
    for wt in worktrees_to_remove:
        ctx.git_ops.remove_worktree(repo.root, wt.path, force=True)
        path_text = click.style(str(wt.path), fg="green")
        click.echo(f"✅ Removed: {path_text}")

    click.echo(f"\n{click.style('✅ Consolidation complete', fg='green', bold=True)}")
