"""Consolidate worktrees by removing others containing branches from current stack."""

import subprocess
from pathlib import Path

import click

from workstack.cli.core import discover_repo_context
from workstack.core.context import WorkstackContext


@click.command("consolidate")
@click.argument("branch", required=False, default=None)
@click.option(
    "--name",
    type=str,
    default=None,
    help="Create and consolidate into a new worktree with this name",
)
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be removed without executing",
)
@click.pass_obj
def consolidate_cmd(
    ctx: WorkstackContext, branch: str | None, name: str | None, force: bool, dry_run: bool
) -> None:
    """Consolidate stack branches into a single worktree.

    This command removes other worktrees that contain branches from the current
    stack, ensuring branches exist in only one worktree. This is useful before
    stack-wide operations like 'gt restack'.

    BRANCH: Optional branch name. If provided, consolidate only from trunk up to
    this branch (partial consolidation). If omitted, consolidate entire stack.

    \b
    Examples:
      # Consolidate entire stack into current worktree
      $ workstack consolidate

      # Consolidate trunk → feat-2 only (leaves feat-3+ in separate worktrees)
      $ workstack consolidate feat-2

      # Create new worktree "my-stack" and consolidate entire stack into it
      $ workstack consolidate --name my-stack

      # Consolidate trunk → feat-2 into new worktree "my-partial"
      $ workstack consolidate feat-2 --name my-partial

      # Preview changes without executing
      $ workstack consolidate feat-2 --dry-run

      # Skip confirmation prompt
      $ workstack consolidate --force

    Safety checks:
    - Aborts if any worktree in the stack has uncommitted changes
    - Preserves the current worktree (or creates new one with --name)
    - Shows preview before removal (unless --force)
    - Never removes root worktree
    """
    # Get current worktree and branch
    current_worktree = ctx.cwd
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

    # Validate branch argument if provided
    if branch is not None:
        if branch not in stack_branches:
            click.echo(
                click.style(f"❌ Error: Branch '{branch}' is not in the current stack", fg="red"),
                err=True,
            )
            click.echo("\nCurrent stack:", err=True)
            for b in stack_branches:
                marker = " ← current" if b == current_branch else ""
                click.echo(f"  {click.style(b, fg='cyan')}{marker}", err=True)
            raise SystemExit(1)

    # Determine which portion of the stack to consolidate
    if branch is not None:
        # Find the index of the specified branch
        branch_index = stack_branches.index(branch)
        # Partial stack: from trunk (index 0) up to and including the specified branch
        stack_to_consolidate = stack_branches[: branch_index + 1]
    else:
        # Full stack consolidation (current behavior)
        stack_to_consolidate = stack_branches

    # Get all worktrees
    all_worktrees = ctx.git_ops.list_worktrees(repo.root)

    # Validate --name argument if provided
    if name is not None:
        # Check if a worktree with this name already exists
        existing_names = [wt.path.name for wt in all_worktrees]

        if name in existing_names:
            click.echo(
                click.style(f"❌ Error: Worktree '{name}' already exists", fg="red"), err=True
            )
            click.echo("\nSuggested action:", err=True)
            click.echo("  1. Use a different name", err=True)
            click.echo(f"  2. Remove existing worktree: workstack remove {name}", err=True)
            click.echo(f"  3. Switch to existing: workstack switch {name}", err=True)
            raise SystemExit(1)

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

    # Create new worktree if --name is provided
    if name is not None:
        if not dry_run:
            # Use git worktree add to create new worktree
            # Base it on current branch so branches can be moved into it
            new_worktree_path = repo.root.parent / name
            result = subprocess.run(
                ["git", "worktree", "add", str(new_worktree_path), current_branch],
                cwd=repo.root,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                click.echo(
                    click.style(f"❌ Failed to create worktree '{name}'", fg="red"), err=True
                )
                click.echo(f"\nDetails: {result.stderr}", err=True)
                raise SystemExit(1)

            click.echo(click.style(f"✅ Created new worktree: {name}", fg="green"))
            target_worktree_path = new_worktree_path
        else:
            click.echo(
                click.style(f"[DRY RUN] Would create new worktree: {name}", fg="yellow", bold=True)
            )
            target_worktree_path = current_worktree  # In dry-run, keep current path
    else:
        # Use current worktree as target (existing behavior)
        target_worktree_path = current_worktree

    # Identify worktrees to remove
    # Find worktrees to remove based on partial stack and target worktree
    worktrees_to_remove = []
    target_worktree_resolved = target_worktree_path.resolve()

    for worktree in all_worktrees:
        # Skip if no branch (detached HEAD)
        if worktree.branch is None:
            continue

        # Skip if branch is not in the consolidation range
        if worktree.branch not in stack_to_consolidate:
            continue

        # Skip the target worktree
        if worktree.path.resolve() == target_worktree_resolved:
            continue

        # Never remove root worktree (CRITICAL safety check)
        if worktree.is_root:
            continue

        worktrees_to_remove.append(worktree)

    # Display preview
    if not worktrees_to_remove:
        click.echo("No other worktrees found containing branches from current stack")
        click.echo(f"\nCurrent stack branches: {', '.join(stack_branches)}")
        return

    # Display current stack (or partial stack) with visual indicators
    click.echo("\n" + click.style("Current stack:", bold=True))
    for b in stack_branches:  # Show FULL stack for context
        if b == current_branch:
            marker = f" {click.style('←', fg='bright_green')} current"
            branch_display = click.style(b, fg="bright_green", bold=True)
        elif b in stack_to_consolidate:
            marker = f" {click.style('→', fg='yellow')} consolidating"
            branch_display = click.style(b, fg="yellow")
        else:
            marker = " (keeping separate)"
            branch_display = click.style(b, fg="white", dim=True)

        click.echo(f"  {branch_display}{marker}")

    # Display target worktree info
    if name is not None:
        target_display = click.style(name, fg="cyan", bold=True)
        click.echo(f"\n{click.style('Target worktree:', bold=True)} {target_display} (new)")
    else:
        target_display = click.style(str(current_worktree), fg="cyan")
        click.echo(f"\n{click.style('Target worktree:', bold=True)} {target_display} (current)")

    click.echo(f"\n{click.style('🗑️  Safe to remove (no uncommitted changes):', bold=True)}")
    for wt in worktrees_to_remove:
        branch_text = click.style(wt.branch or "detached", fg="yellow")
        path_text = click.style(str(wt.path), fg="cyan")
        click.echo(f"  - {branch_text} at {path_text}")

    # Inform user about stack restackability
    click.echo()
    click.echo(
        f"ℹ️  Note: Use 'gt restack' on {target_worktree_path} to restack. "
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

    # Auto-switch logic for new worktrees
    if name is not None and not dry_run:
        click.echo(f"Switching to worktree: {click.style(name, fg='cyan', bold=True)}")
        click.echo(f"\n{click.style('ℹ️', fg='blue')} Run this command to switch:")
        click.echo(f"  cd {target_worktree_path}")
