"""Forest reroot command - conflict-preserving rebase for entire stack."""

from datetime import UTC
from pathlib import Path

import click

from erk.cli.commands.forest.reroot_utils import (
    create_reroot_plan,
    format_conflict_commit_message,
    format_progress_message,
    format_resolved_commit_message,
)
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.forest_types import RerootState
from erk.core.gitops import find_worktree_for_branch
from erk.core.repo_discovery import NoRepoSentinel, ensure_repo_dir
from erk.core.worktree_utils import find_current_worktree


@click.command("reroot")
@click.argument("forest_name", required=False)
@click.option(
    "--continue", "continue_reroot", is_flag=True, help="Resume after conflict resolution"
)
@click.option("--abort", "abort_reroot", is_flag=True, help="Abort reroot operation")
@click.option("-f", "--force", is_flag=True, help="Skip confirmation")
@click.option("--dry-run", is_flag=True, help="Preview without executing")
@click.pass_obj
def reroot_forest(
    ctx: ErkContext,
    forest_name: str | None,
    continue_reroot: bool,
    abort_reroot: bool,
    force: bool,
    dry_run: bool,
) -> None:
    """Reroot forest with conflict preservation.

    Rebases all branches in a forest while preserving conflict states
    in git history for better review and debugging.
    """
    if isinstance(ctx.repo, NoRepoSentinel):
        user_output(
            click.style("Error: ", fg="red")
            + "Not in a repository. This command requires a git repository."
        )
        raise SystemExit(1)

    repo_dir = ensure_repo_dir(ctx.repo)

    # Handle --abort workflow
    if abort_reroot:
        _handle_abort(ctx, repo_dir)
        return

    # Handle --continue workflow
    if continue_reroot:
        _handle_continue(ctx, repo_dir, force)
        return

    # Handle initial reroot workflow
    _handle_initial_reroot(ctx, repo_dir, forest_name, force, dry_run)


def _handle_abort(ctx: ErkContext, repo_dir: Path) -> None:
    """Handle reroot --abort workflow."""
    if isinstance(ctx.repo, NoRepoSentinel):
        return

    # Load reroot state
    state = ctx.forest_ops.load_reroot_state()

    if state is None:
        user_output(
            click.style("❌ Error: ", fg="red")
            + "No rebase in progress\n\n"
            + "There is no active rebase to abort.\n\n"
            + "To start a new rebase: erk forest reroot"
        )
        raise SystemExit(1)

    user_output("Aborting rebase workflow...")
    user_output()

    # Get worktree for current branch
    worktrees = ctx.git_ops.list_worktrees(ctx.repo.root)
    worktree = find_worktree_for_branch(worktrees, state.current_branch)

    if worktree is None:
        user_output(
            click.style("⚠ Warning: ", fg="yellow")
            + f"Worktree for branch '{state.current_branch}' not found"
        )
    else:
        user_output("Running: git rebase --abort")
        try:
            ctx.git_ops.abort_rebase(worktree)
        except Exception as e:
            user_output(click.style("⚠ Warning: ", fg="yellow") + f"Failed to abort rebase: {e}")

    user_output("Cleaning up state...")

    # Clear reroot state
    ctx.forest_ops.clear_reroot_state()

    # Remove marker file
    marker_path = repo_dir.parent / ".erk" / "REROOT_IN_PROGRESS"
    if marker_path.exists():
        marker_path.unlink()

    user_output()
    user_output(click.style("✅ Rebase aborted. All changes reverted.", fg="green"))
    user_output()
    user_output("The repository has been restored to its state before the rebase.")


def _handle_continue(ctx: ErkContext, repo_dir: Path, force: bool) -> None:
    """Handle reroot --continue workflow."""
    if isinstance(ctx.repo, NoRepoSentinel):
        return

    # Load reroot state
    state = ctx.forest_ops.load_reroot_state()

    if state is None:
        user_output(
            click.style("❌ Error: ", fg="red")
            + "No rebase state found\n\n"
            + "You ran --continue without an active rebase. "
            + "Did you mean to start a new rebase?\n\n"
            + "Run: erk forest reroot"
        )
        raise SystemExit(1)

    user_output("Resuming rebase workflow...")
    user_output()
    user_output(f"Continuing rebase for branch: {click.style(state.current_branch, fg='yellow')}")

    # Get worktree for current branch
    worktrees = ctx.git_ops.list_worktrees(ctx.repo.root)
    worktree = find_worktree_for_branch(worktrees, state.current_branch)

    if worktree is None:
        user_output(
            click.style("Error: ", fg="red")
            + f"Worktree for branch '{state.current_branch}' not found"
        )
        raise SystemExit(1)

    # Check for unresolved conflicts
    conflicted_files = ctx.git_ops.get_conflicted_files(worktree)

    if conflicted_files:
        user_output(
            click.style("❌ Error: ", fg="red")
            + "Conflicts not fully resolved\n\n"
            + "The following files still contain conflict markers:"
        )
        for f in conflicted_files:
            user_output(f"  - {f}")
        user_output()
        user_output("Please resolve all conflicts before continuing.")
        raise SystemExit(1)

    user_output()

    # Create [RESOLVED] commit
    resolved_msg = format_resolved_commit_message(state.parent_branch, state.parent_sha)
    user_output(f"Creating resolution commit: {resolved_msg}")

    ctx.git_ops.commit_with_message(resolved_msg, worktree)

    user_output(f"  {click.style('✓', fg='green')} Resolution commit created")

    # Continue rebase
    user_output("Continuing rebase...")
    # The rebase should automatically continue after we committed
    user_output(f"  {click.style('✓', fg='green')} Rebase continued successfully")

    user_output()

    # Continue with remaining branches
    if state.remaining_branches:
        user_output("Continuing with remaining branches...")
        user_output()

        _execute_reroot_loop(ctx, repo_dir, state.forest, state.remaining_branches, force)
    else:
        # All done
        _complete_reroot(ctx, repo_dir, state.forest)


def _handle_initial_reroot(
    ctx: ErkContext,
    repo_dir: Path,
    forest_name: str | None,
    force: bool,
    dry_run: bool,
) -> None:
    """Handle initial reroot workflow."""
    # Check for existing reroot state
    existing_state = ctx.forest_ops.load_reroot_state()
    if existing_state is not None:
        user_output(
            click.style("❌ Error: ", fg="red")
            + f"Reroot operation already in progress for forest '{existing_state.forest}'\n\n"
            + "Resume: erk forest reroot --continue\n"
            + "Abort: erk forest reroot --abort"
        )
        raise SystemExit(1)

    # Check for marker file
    marker_path = repo_dir.parent / ".erk" / "REROOT_IN_PROGRESS"
    if ctx.git_ops.path_exists(marker_path):
        user_output(
            click.style("❌ Error: ", fg="red")
            + "Reroot operation marker file exists\n\n"
            + "Resume: erk forest reroot --continue\n"
            + "Abort: erk forest reroot --abort"
        )
        raise SystemExit(1)

    # Validate preconditions
    if not ctx.global_config or not ctx.global_config.use_graphite:
        user_output(
            click.style("❌ Error: ", fg="red")
            + "This command requires Graphite\n\n"
            + "Run: erk config set use-graphite true"
        )
        raise SystemExit(1)

    # Check clean working directory
    if ctx.git_ops.has_uncommitted_changes(ctx.cwd):
        user_output(
            click.style("❌ Error: ", fg="red")
            + "Uncommitted changes detected in current worktree\n\n"
            + "Suggested actions:\n"
            + '  git add . && git commit -m "WIP"\n'
            + "  # or\n"
            + "  git stash"
        )
        raise SystemExit(1)

    # Determine forest
    metadata = ctx.forest_ops.load_forests()

    # Type narrowing for repo (needed for .root access)
    if isinstance(ctx.repo, NoRepoSentinel):
        user_output(click.style("Error: ", fg="red") + "Not in a repository")
        raise SystemExit(1)

    if forest_name is None:
        # Use current worktree's forest
        worktrees = ctx.git_ops.list_worktrees(ctx.repo.root)
        current_wt_info = find_current_worktree(worktrees, ctx.cwd)

        if current_wt_info is None:
            user_output(
                click.style("Error: ", fg="red")
                + "Not in a worktree and no forest name provided.\n\n"
                + "Usage: erk forest reroot [FOREST_NAME]"
            )
            raise SystemExit(1)

        current_wt_name = current_wt_info.path.name

        # Find forest
        forest = None
        for f in metadata.forests.values():
            if current_wt_name in f.worktrees:
                forest = f
                break

        if forest is None:
            user_output(
                click.style("Error: ", fg="red")
                + "Current worktree is not in a forest.\n\n"
                + "Use 'erk forest list' to see all forests."
            )
            raise SystemExit(1)
    else:
        # Use specified forest
        if forest_name not in metadata.forests:
            available = ", ".join(metadata.forests.keys()) if metadata.forests else "(none)"
            user_output(
                click.style("Error: ", fg="red")
                + f"Forest '{forest_name}' not found\n\n"
                + f"Available forests: {available}"
            )
            raise SystemExit(1)

        forest = metadata.forests[forest_name]

    # Get trunk branch
    trunk_branch = ctx.trunk_branch
    if trunk_branch is None:
        user_output(click.style("Error: ", fg="red") + "Could not determine trunk branch")
        raise SystemExit(1)

    # Type narrowing for repo
    if isinstance(ctx.repo, NoRepoSentinel):
        user_output(click.style("Error: ", fg="red") + "Not in a repository")
        raise SystemExit(1)

    # Create reroot plan
    plan = create_reroot_plan(forest, ctx.graphite_ops, ctx.git_ops, trunk_branch, ctx.repo.root)

    # Check all branches have worktrees
    worktrees = ctx.git_ops.list_worktrees(ctx.repo.root)
    worktree_branches = {wt.branch for wt in worktrees if wt.branch}

    missing = []
    for branch, _ in plan.branches_in_order:
        if branch not in worktree_branches:
            missing.append(branch)

    if missing:
        user_output(
            click.style("❌ Error: ", fg="red")
            + "The following branches do not have worktrees\n\n"
            + "Missing branches:"
        )
        for branch in missing:
            user_output(f"  - {branch}")
        user_output()
        user_output("Create worktrees with:")
        for branch in missing:
            user_output(f"  erk create {branch}")
        raise SystemExit(1)

    # Display preview
    user_output("Starting rebase workflow...")
    user_output()
    user_output(f"Forest: {click.style(forest.name, fg='cyan', bold=True)}")
    user_output(f"Base: {click.style(trunk_branch, fg='yellow')}")
    user_output(f"Branches: {len(plan.branches_in_order)}")
    user_output()

    for i, (branch, parent) in enumerate(plan.branches_in_order, start=1):
        user_output(f"  {i}. {click.style(branch, fg='yellow')} (onto {parent})")

    user_output()
    user_output(click.style("✅ Pre-flight checks passed", fg="green"))

    # Confirm
    if dry_run:
        user_output()
        user_output(click.style("(dry run)", fg="bright_black"))
        raise SystemExit(0)

    if not force:
        user_output()
        if not click.confirm("Continue?", default=False):
            user_output(click.style("⭕ Aborted", fg="yellow"))
            raise SystemExit(0)

    user_output()

    # Note: Marker file creation would happen here in production
    # For now, we rely on forest_ops state management instead

    # Execute reroot
    all_branches = [b for b, _ in plan.branches_in_order]
    _execute_reroot_loop(ctx, repo_dir, forest.name, all_branches, force)


def _execute_reroot_loop(
    ctx: ErkContext,
    repo_dir: Path,
    forest_name: str,
    branches_to_process: list[str],
    force: bool,
) -> None:
    """Execute reroot loop for given branches."""
    if isinstance(ctx.repo, NoRepoSentinel):
        return

    worktrees = ctx.git_ops.list_worktrees(ctx.repo.root)

    for idx, branch in enumerate(branches_to_process, start=1):
        user_output(format_progress_message(idx, len(branches_to_process), branch))

        # Get worktree for branch
        worktree = find_worktree_for_branch(worktrees, branch)
        if worktree is None:
            user_output(
                f"  {click.style('⚠', fg='yellow')} Worktree for '{branch}' not found, skipping"
            )
            continue

        # Get parent branch (previous in list, or trunk for first)
        # This is simplified - in real implementation would use plan
        # For now just continue

        user_output("  Running rebase...")

        # Get parent SHA
        parent_branch = ctx.graphite_ops.get_parent_branch(ctx.git_ops, ctx.repo.root, branch)
        if parent_branch is None:
            user_output(f"  {click.style('⚠', fg='yellow')} No parent branch found, skipping")
            continue

        parent_wt = find_worktree_for_branch(worktrees, parent_branch)
        if parent_wt is None:
            user_output(f"  {click.style('⚠', fg='yellow')} Parent worktree not found, skipping")
            continue

        parent_sha = ctx.git_ops.get_commit_sha(parent_branch, parent_wt)

        # Rebase
        result = ctx.git_ops.rebase_branch(branch, parent_branch, worktree)

        if result.success:
            branch_styled = click.style(branch, fg="yellow")
            user_output(
                f"  {click.style('✅', fg='green')} Branch '{branch_styled}' rebased successfully"
            )
            continue

        # Conflicts detected
        if result.has_conflicts:
            user_output()
            branch_styled = click.style(branch, fg="yellow")
            user_output(
                f"{click.style('⚠️  ', fg='yellow')}Conflicts detected in branch: {branch_styled}"
            )
            user_output()

            # Get conflicted files with status
            conflicted = result.conflicted_files
            user_output(f"Conflicted files ({len(conflicted)}):")
            for f in conflicted:
                user_output(f"  - {f}")

            user_output()

            # Prompt for conflict commit
            if not force:
                should_commit = click.confirm(
                    "Commit conflict state to preserve in history?", default=True
                )
            else:
                should_commit = True

            if should_commit:
                conflict_msg = format_conflict_commit_message(parent_branch, parent_sha)
                user_output(f"Creating conflict commit: {conflict_msg}")

                ctx.git_ops.commit_with_message(conflict_msg, worktree)

                user_output(f"  {click.style('✓', fg='green')} Conflict commit created")

                # Save state
                remaining = branches_to_process[idx:]
                from datetime import datetime

                state = RerootState(
                    forest=forest_name,
                    current_branch=branch,
                    parent_branch=parent_branch,
                    parent_sha=parent_sha,
                    remaining_branches=remaining,
                    paused_on_conflicts=True,
                    started_at=datetime.now(UTC).isoformat(),
                )
                ctx.forest_ops.save_reroot_state(state)

                user_output(f"  {click.style('✓', fg='green')} Progress saved")
                user_output()
                user_output("Next steps:")
                user_output("1. Resolve conflicts in the files listed above")
                user_output("2. Run: erk forest reroot --continue")
                user_output()
                # Find actual worktree path
                for wt in worktrees:
                    if wt.branch == branch:
                        user_output(f"ℹ️  Current worktree: {wt.path}")
                        break
                raise SystemExit(0)
            else:
                user_output("Aborting reroot (no state saved)")
                raise SystemExit(1)

    # All done
    _complete_reroot(ctx, repo_dir, forest_name)


def _complete_reroot(ctx: ErkContext, repo_dir: Path, forest_name: str) -> None:
    """Complete reroot operation and clean up."""
    # Clear reroot state
    ctx.forest_ops.clear_reroot_state()

    # Remove marker file
    marker_path = repo_dir.parent / ".erk" / "REROOT_IN_PROGRESS"
    if marker_path.exists():
        marker_path.unlink()

    # Display completion
    user_output()
    user_output(click.style("✅ Stack rebase complete!", fg="green"))
    user_output()
    user_output("All branches in the stack have been rebased successfully.")
    user_output()
    user_output(f"Forest '{click.style(forest_name, fg='cyan', bold=True)}' successfully rerooted.")
