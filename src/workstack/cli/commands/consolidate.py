"""Consolidate worktrees by removing others containing branches from current stack."""

import time
from pathlib import Path

import click

from workstack.cli.activation import render_activation_script
from workstack.cli.core import discover_repo_context, worktree_path_for
from workstack.cli.output import machine_output, user_output
from workstack.core.consolidation_utils import calculate_stack_range, create_consolidation_plan
from workstack.core.context import WorkstackContext, create_context
from workstack.core.repo_discovery import ensure_workstacks_dir


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
@click.option(
    "--down",
    is_flag=True,
    help="Only consolidate downstack (trunk to current branch). Default is entire stack.",
)
@click.option(
    "--script",
    is_flag=True,
    hidden=True,
    help="Output shell script for directory change instead of messages.",
)
@click.pass_obj
def consolidate_cmd(
    ctx: WorkstackContext,
    branch: str | None,
    name: str | None,
    force: bool,
    dry_run: bool,
    down: bool,
    script: bool,
) -> None:
    """Consolidate stack branches into a single worktree.

    By default, consolidates full stack (trunk to leaf). With --down, consolidates
    only downstack branches (trunk to current).

    This command removes other worktrees that contain branches from the stack,
    ensuring branches exist in only one worktree. This is useful before
    stack-wide operations like 'gt restack'.

    BRANCH: Optional branch name. If provided, consolidate only from trunk up to
    this branch (partial consolidation). Cannot be used with --down.

    \b
    Examples:
      # Consolidate full stack into current worktree (default)
      $ workstack consolidate

      # Consolidate only downstack (trunk to current)
      $ workstack consolidate --down

      # Consolidate trunk → feat-2 only (leaves feat-3+ in separate worktrees)
      $ workstack consolidate feat-2

      # Create new worktree "my-stack" and consolidate full stack into it
      $ workstack consolidate --name my-stack

      # Consolidate downstack into new worktree
      $ workstack consolidate --down --name my-partial

      # Preview changes without executing
      $ workstack consolidate --dry-run

      # Skip confirmation prompt
      $ workstack consolidate --force

    Safety checks:
    - Aborts if any worktree being consolidated has uncommitted changes
    - Preserves the current worktree (or creates new one with --name)
    - Shows preview before removal (unless --force)
    - Never removes root worktree
    """
    # During dry-run, always show output regardless of shell integration
    if dry_run:
        script = False

    # Validate that --down and BRANCH are not used together
    if down and branch is not None:
        user_output(click.style("❌ Error: Cannot use --down with BRANCH argument", fg="red"))
        user_output(
            "Use either --down (consolidate trunk to current) or "
            "BRANCH (consolidate trunk to BRANCH)"
        )
        raise SystemExit(1)

    # Get current worktree and branch
    current_worktree = ctx.cwd
    current_branch = ctx.git_ops.get_current_branch(current_worktree)

    if current_branch is None:
        user_output("Error: Current worktree is in detached HEAD state")
        user_output("Checkout a branch before running consolidate")
        raise SystemExit(1)

    # Get repository root
    repo = discover_repo_context(ctx, current_worktree)

    # Get current branch's stack
    stack_branches = ctx.graphite_ops.get_branch_stack(ctx.git_ops, repo.root, current_branch)
    if stack_branches is None:
        user_output(f"Error: Branch '{current_branch}' is not tracked by Graphite")
        user_output(
            "Run 'gt repo init' to initialize Graphite, or use 'gt track' to track this branch"
        )
        raise SystemExit(1)

    # Validate branch argument if provided
    if branch is not None:
        if branch not in stack_branches:
            user_output(
                click.style(f"❌ Error: Branch '{branch}' is not in the current stack", fg="red")
            )
            user_output("\nCurrent stack:")
            for b in stack_branches:
                marker = " ← current" if b == current_branch else ""
                user_output(f"  {click.style(b, fg='cyan')}{marker}")
            raise SystemExit(1)

    # Determine which portion of the stack to consolidate (now handled by utility)
    # This will be used in create_consolidation_plan() below

    # Get all worktrees
    all_worktrees = ctx.git_ops.list_worktrees(repo.root)

    # Validate --name argument if provided
    if name is not None:
        # Check if a worktree with this name already exists
        existing_names = [wt.path.name for wt in all_worktrees]

        if name in existing_names:
            user_output(click.style(f"❌ Error: Worktree '{name}' already exists", fg="red"))
            user_output("\nSuggested action:")
            user_output("  1. Use a different name")
            user_output(f"  2. Remove existing worktree: workstack remove {name}")
            user_output(f"  3. Switch to existing: workstack switch {name}")
            raise SystemExit(1)

    # Calculate stack range early (needed for safety check)
    # If --down is set, force end_branch to be current_branch
    end_branch = current_branch if down else branch
    stack_to_consolidate = calculate_stack_range(stack_branches, end_branch)

    # Check worktrees in stack for uncommitted changes
    # Only check worktrees that will actually be removed (skip root and current)
    worktrees_with_changes: list[Path] = []
    for wt in all_worktrees:
        if wt.branch not in stack_to_consolidate:
            continue
        # Skip root worktree (never removed)
        if wt.is_root:
            continue
        # Skip current worktree (consolidation target, never removed)
        if wt.path.resolve() == current_worktree.resolve():
            continue
        if ctx.git_ops.path_exists(wt.path) and ctx.git_ops.has_uncommitted_changes(wt.path):
            worktrees_with_changes.append(wt.path)

    if worktrees_with_changes:
        user_output(
            click.style("Error: Uncommitted changes detected in worktrees:", fg="red", bold=True)
        )
        for wt_path in worktrees_with_changes:
            user_output(f"  - {wt_path}")
        user_output("\nCommit or stash changes before running consolidate")
        raise SystemExit(1)

    # Safety check passed - all worktrees are clean
    user_output(
        click.style("✅ Safety check: All worktrees have no uncommitted changes", fg="green")
    )
    user_output()

    # Create new worktree if --name is provided
    # Track temp branch name for cleanup after source worktree removal
    temp_branch_name: str | None = None

    if name is not None:
        if not dry_run:
            # Generate temporary branch name to avoid "already used by worktree" error
            # when the source worktree and new worktree would have the same branch checked out
            temp_branch_name = f"temp-consolidate-{int(time.time())}"

            # Use proper workstacks directory path resolution
            workstacks_dir = ensure_workstacks_dir(repo)
            new_worktree_path = worktree_path_for(workstacks_dir, name)

            # Create temporary branch on current commit (doesn't checkout)
            # GitOps operations use check=True, so failures raise CalledProcessError
            ctx.git_ops.create_branch(current_worktree, temp_branch_name, current_branch)

            # Checkout temporary branch in source worktree to free up the original branch
            ctx.git_ops.checkout_branch(current_worktree, temp_branch_name)

            # Create new worktree with original branch
            # (now available since source is on temp branch)
            ctx.git_ops.add_worktree(
                repo.root,
                new_worktree_path,
                branch=current_branch,
                ref=None,
                create_branch=False,
            )

            user_output(click.style(f"✅ Created new worktree: {name}", fg="green"))

            # Change to new worktree directory BEFORE removing source worktree
            # This prevents the shell from being in a deleted directory
            if not script and ctx.git_ops.safe_chdir(new_worktree_path):
                # Regenerate context with new cwd (context is immutable)
                ctx = create_context(dry_run=ctx.dry_run)
                user_output(click.style("✅ Changed directory to new worktree", fg="green"))

            target_worktree_path = new_worktree_path
        else:
            user_output(
                click.style(f"[DRY RUN] Would create new worktree: {name}", fg="yellow", bold=True)
            )
            target_worktree_path = current_worktree  # In dry-run, keep current path
    else:
        # Use current worktree as target (existing behavior)
        target_worktree_path = current_worktree

    # Create consolidation plan using utility function
    # Use the same end_branch logic as calculated above
    plan = create_consolidation_plan(
        all_worktrees=all_worktrees,
        stack_branches=stack_branches,
        end_branch=end_branch,
        target_worktree_path=target_worktree_path,
        source_worktree_path=current_worktree if name is not None else None,
    )

    # Extract data from plan for easier reference
    worktrees_to_remove = plan.worktrees_to_remove
    stack_to_consolidate = plan.stack_to_consolidate

    # Display preview
    if not worktrees_to_remove:
        # If using --name, we still need to remove source worktree even if no other worktrees exist
        if name is None:
            user_output("No other worktrees found containing branches from current stack")
            user_output(f"\nCurrent stack branches: {', '.join(stack_branches)}")
            return
        # Continue to source worktree removal when using --name

    # Display current stack (or partial stack) with visual indicators
    user_output("\n" + click.style("Current stack:", bold=True))
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

        user_output(f"  {branch_display}{marker}")

    # Display target worktree info
    if name is not None:
        target_display = click.style(name, fg="cyan", bold=True)
        user_output(f"\n{click.style('Target worktree:', bold=True)} {target_display} (new)")
    else:
        target_display = click.style(str(current_worktree), fg="cyan")
        user_output(f"\n{click.style('Target worktree:', bold=True)} {target_display} (current)")

    user_output(f"\n{click.style('🗑️  Safe to remove (no uncommitted changes):', bold=True)}")
    for wt in worktrees_to_remove:
        branch_text = click.style(wt.branch or "detached", fg="yellow")
        path_text = click.style(str(wt.path), fg="cyan")
        user_output(f"  - {branch_text} at {path_text}")

    # Show source worktree removal if creating new worktree
    if name is not None:
        path_text = click.style(str(current_worktree), fg="cyan")
        user_output(f"  - source worktree at {path_text}")

    # Inform user about stack restackability
    user_output()
    user_output(
        f"ℹ️  Note: Use 'gt restack' on {target_worktree_path} to restack. "
        "All branches are preserved."
    )

    # Exit if dry-run
    if dry_run:
        user_output(f"\n{click.style('[DRY RUN] No changes made', fg='yellow', bold=True)}")
        return

    # Get confirmation unless --force or --script
    if not force and not script:
        user_output()
        if not click.confirm(
            click.style("All worktrees are clean. Proceed with removal?", fg="yellow", bold=True),
            default=False,
        ):
            user_output(click.style("⭕ Aborted", fg="red", bold=True))
            return

    # Remove worktrees
    user_output()
    for wt in worktrees_to_remove:
        ctx.git_ops.remove_worktree(repo.root, wt.path, force=True)
        path_text = click.style(str(wt.path), fg="green")
        user_output(f"✅ Removed: {path_text}")

    # Remove source worktree if a new worktree was created
    if name is not None:
        ctx.git_ops.remove_worktree(repo.root, current_worktree.resolve(), force=True)
        path_text = click.style(str(current_worktree), fg="green")
        user_output(f"✅ Removed source worktree: {path_text}")

        # Delete temporary branch after source worktree is removed
        # (can't delete while it's checked out in the source worktree)
        if temp_branch_name is not None:
            ctx.git_ops.delete_branch(repo.root, temp_branch_name, force=True)

    user_output(f"\n{click.style('✅ Consolidation complete', fg='green', bold=True)}")

    # Early return when no worktree switch (consolidating into current worktree)
    # Makes it explicit that no script is needed in this case
    if name is None:
        return  # No script needed when not switching worktrees

    # Shell integration: generate script to activate new worktree
    if script and not dry_run:
        script_content = render_activation_script(
            worktree_path=target_worktree_path,
            final_message='echo "✓ Switched to consolidated worktree."',
            comment="work activate-script (consolidate)",
        )
        result = ctx.script_writer.write_activation_script(
            script_content,
            command_name="consolidate",
            comment=f"activate {name}",
        )
        machine_output(str(result.path), nl=False)
    elif not dry_run:
        # Manual cd instruction when not in script mode
        user_output(f"Switching to worktree: {click.style(name, fg='cyan', bold=True)}")
        user_output(f"\n{click.style('ℹ️', fg='blue')} Run this command to switch:")
        user_output(f"  cd {target_worktree_path}")
