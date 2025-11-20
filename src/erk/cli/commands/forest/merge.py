"""Forest merge command - consolidate forest into single worktree."""

import click

from erk.cli.commands.forest.merge_utils import (
    check_uncommitted_changes,
    create_forest_merge_plan,
)
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, ensure_repo_dir
from erk.core.worktree_utils import find_current_worktree


@click.command("merge")
@click.argument("forest_name", required=False)
@click.option("--into", "target_worktree", type=str, help="Target worktree name")
@click.option("-f", "--force", is_flag=True, help="Skip confirmation")
@click.option("--dry-run", is_flag=True, help="Preview without executing")
@click.pass_obj
def merge_forest(
    ctx: ErkContext,
    forest_name: str | None,
    target_worktree: str | None,
    force: bool,
    dry_run: bool,
) -> None:
    """Merge forest into single worktree.

    Removes all worktrees except the target, consolidating the forest
    into a single worktree with all branches.
    """
    if isinstance(ctx.repo, NoRepoSentinel):
        user_output(
            click.style("Error: ", fg="red")
            + "Not in a repository. This command requires a git repository."
        )
        raise SystemExit(1)

    repo_dir = ensure_repo_dir(ctx.repo)

    # Determine forest
    metadata = ctx.forest.load_forests()

    if forest_name is None:
        # Use current worktree's forest
        worktrees = ctx.git.list_worktrees(ctx.repo.root)
        current_wt_info = find_current_worktree(worktrees, ctx.cwd)

        if current_wt_info is None:
            user_output(
                click.style("Error: ", fg="red")
                + "Not in a worktree and no forest name provided.\n\n"
                + "Usage: erk forest merge [FOREST_NAME]"
            )
            raise SystemExit(1)

        current_wt_name = current_wt_info.path.name

        # Find forest for current worktree
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

    # Check if forest has only one worktree
    if len(forest.worktrees) <= 1:
        user_output(
            f"Forest '{click.style(forest.name, fg='cyan', bold=True)}' "
            f"only has one worktree. Nothing to merge."
        )
        raise SystemExit(0)

    # Determine current worktree for plan
    worktrees = ctx.git.list_worktrees(ctx.repo.root)
    current_wt_info = find_current_worktree(worktrees, ctx.cwd)
    current_wt_name = current_wt_info.path.name if current_wt_info else None

    # Create merge plan
    try:
        plan = create_forest_merge_plan(forest, target_worktree, current_wt_name)
    except ValueError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from None

    # Check for uncommitted changes in worktrees to remove
    worktrees_dir = repo_dir / "worktrees"
    dirty_worktrees = check_uncommitted_changes(plan.worktrees_to_remove, ctx.git, worktrees_dir)

    if dirty_worktrees:
        user_output(
            click.style("Error: ", fg="red")
            + "Uncommitted changes in worktrees: "
            + ", ".join(dirty_worktrees)
            + "\n\n"
            + "Commit or stash changes first."
        )
        raise SystemExit(1)

    # Display preview
    forest_styled = click.style(forest.name, fg="cyan", bold=True)
    target_styled = click.style(plan.target_worktree, fg="yellow")

    user_output(
        f"This will merge forest '{forest_styled}' "
        f"({len(forest.worktrees)} worktrees) into worktree '{target_styled}'."
    )
    user_output()
    user_output("Worktrees to be removed:")

    for wt in plan.worktrees_to_remove:
        user_output(f"  • {click.style(wt, fg='yellow')}")

    user_output()

    # Confirm unless --force or --dry-run
    if dry_run:
        user_output(click.style("(dry run)", fg="bright_black"))
        raise SystemExit(0)

    if not force:
        if not click.confirm("Continue?", default=False):
            user_output(click.style("⭕ Aborted", fg="yellow"))
            raise SystemExit(0)

    # Execute merge
    user_output()

    for wt_name in plan.worktrees_to_remove:
        wt_path = worktrees_dir / wt_name

        if not wt_path.exists():
            user_output(
                f"  {click.style('⚠', fg='yellow')} Worktree '{wt_name}' not found, skipping"
            )
            continue

        user_output(f"Removing worktree '{click.style(wt_name, fg='yellow')}'...")

        ctx.git.remove_worktree(ctx.repo.root, wt_path, force=False)

        user_output(
            f"  {click.style('✓', fg='green')} Removed worktree: "
            f"{click.style(wt_name, fg='white', dim=True)}"
        )

    # Remove forest from metadata
    user_output()
    user_output("Removing forest metadata...")

    updated_forests = {name: f for name, f in metadata.forests.items() if name != forest.name}
    updated_metadata = metadata.__class__(forests=updated_forests)

    ctx.forest.save_forests(updated_metadata)

    user_output(
        f"  {click.style('✓', fg='green')} Forest "
        f"'{click.style(forest.name, fg='cyan', bold=True)}' removed"
    )

    # Display results
    user_output()
    user_output(
        click.style("✅ Merge complete!", fg="green")
        + f" Removed {len(plan.worktrees_to_remove)} worktrees."
    )
    user_output()
    user_output(
        f"All branches are now in worktree '{click.style(plan.target_worktree, fg='yellow')}'."
    )
