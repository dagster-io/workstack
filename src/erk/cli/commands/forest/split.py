"""Forest split command - convert single worktree into forest."""

import click

from erk.cli.commands.forest.split_utils import (
    create_forest_split_plan,
)
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.forest_utils import add_worktree_to_forest, create_forest
from erk.core.naming_utils import ensure_unique_worktree_name, sanitize_worktree_name
from erk.core.repo_discovery import NoRepoSentinel, ensure_repo_dir


@click.command("split")
@click.argument("forest_name", required=False)
@click.option("--up", is_flag=True, help="Only split upstack branches")
@click.option("--down", is_flag=True, help="Only split downstack branches")
@click.option("-f", "--force", is_flag=True, help="Skip confirmation")
@click.option("--dry-run", is_flag=True, help="Preview without executing")
@click.pass_obj
def split_forest(
    ctx: ErkContext,
    forest_name: str | None,
    up: bool,
    down: bool,
    force: bool,
    dry_run: bool,
) -> None:
    """Split worktree into forest of individual worktrees.

    Creates separate worktrees for each branch in the stack, organizing
    them into a named forest collection.
    """
    # Validate flags
    if up and down:
        user_output(click.style("Error: ", fg="red") + "Cannot specify both --up and --down")
        raise SystemExit(1)

    if isinstance(ctx.repo, NoRepoSentinel):
        user_output(
            click.style("Error: ", fg="red")
            + "Not in a repository. This command requires a git repository."
        )
        raise SystemExit(1)

    repo_dir = ensure_repo_dir(ctx.repo)

    # Get current branch
    current_branch = ctx.git.get_current_branch(ctx.repo.root)
    if current_branch is None:
        user_output(click.style("Error: ", fg="red") + "Could not determine current branch")
        raise SystemExit(1)

    # Get trunk branch
    trunk_branch = ctx.trunk_branch
    if trunk_branch is None:
        user_output(click.style("Error: ", fg="red") + "Could not determine trunk branch")
        raise SystemExit(1)

    # Get stack
    stack_branches = ctx.graphite.get_branch_stack(ctx.git, ctx.repo.root, current_branch)

    if stack_branches is None:
        user_output(
            click.style("Error: ", fg="red") + f"Could not get stack for branch '{current_branch}'"
        )
        raise SystemExit(1)

    # Determine direction
    direction = None
    if up:
        direction = "up"
    elif down:
        direction = "down"

    # Get existing worktrees
    existing_worktrees = ctx.git.list_worktrees(ctx.repo.root)

    # Load forest metadata
    forest_metadata = ctx.forest.load_forests()

    # Create split plan
    plan = create_forest_split_plan(
        stack_branches,
        current_branch,
        trunk_branch,
        existing_worktrees,
        direction,
        forest_name,
        forest_metadata,
    )

    # Check if there's anything to split
    if not plan.branches_to_split:
        user_output("Current worktree contains only one branch. Nothing to split.")
        raise SystemExit(0)

    # Display preview
    user_output(
        f"Current worktree '{click.style(current_branch, fg='yellow')}' "
        f"contains {len(stack_branches)} branches."
    )
    user_output()
    forest_styled = click.style(plan.forest_name, fg="cyan", bold=True)
    total = len(plan.branches_to_split) + 1  # +1 for current branch
    user_output(f"Forest '{forest_styled}' will contain {total} worktrees:")

    # Current worktree
    user_output(f"  • {click.style(current_branch, fg='yellow')} [{current_branch}] (current)")

    # New worktrees
    for branch in plan.branches_to_split:
        user_output(
            f"  • {click.style(branch, fg='yellow')} [{branch}] {click.style('(new)', fg='green')}"
        )

    user_output()

    # Confirm unless --force or --dry-run
    if dry_run:
        user_output(click.style("(dry run)", fg="bright_black"))
        raise SystemExit(0)

    if not force:
        if not click.confirm("Continue?", default=False):
            user_output(click.style("⭕ Aborted", fg="yellow"))
            raise SystemExit(0)

    # Execute split
    user_output()
    worktrees_dir = repo_dir / "worktrees"

    created_worktrees = [current_branch]  # Current branch already has worktree

    for branch in plan.branches_to_split:
        # Sanitize and ensure unique name
        base_name = sanitize_worktree_name(branch)
        unique_name = ensure_unique_worktree_name(base_name, worktrees_dir, ctx.git)

        # Create worktree path
        worktree_path = worktrees_dir / unique_name

        user_output(f"Creating worktree for branch '{click.style(branch, fg='yellow')}'...")

        # Add worktree via git_ops
        ctx.git.add_worktree(
            repo_root=ctx.repo.root,
            path=worktree_path,
            branch=branch,
            ref=None,
            create_branch=False,
        )

        created_worktrees.append(unique_name)

        user_output(
            f"  {click.style('✓', fg='green')} Created worktree: "
            f"{click.style(str(worktree_path), fg='green')}"
        )

    # Update forest metadata
    user_output()
    user_output("Updating forest metadata...")

    metadata = ctx.forest.load_forests()

    if plan.forest_name in metadata.forests:
        # Add to existing forest
        forest = metadata.forests[plan.forest_name]
        for wt_name in created_worktrees:
            if wt_name not in forest.worktrees:
                forest = add_worktree_to_forest(forest, wt_name)

        # Update metadata
        updated_forests = metadata.forests.copy()
        updated_forests[plan.forest_name] = forest
        updated_metadata = metadata.__class__(forests=updated_forests)
    else:
        # Create new forest
        new_forest = create_forest(
            name=plan.forest_name,
            worktrees=created_worktrees,
            root_branch=trunk_branch,
        )

        updated_forests = metadata.forests.copy()
        updated_forests[plan.forest_name] = new_forest
        updated_metadata = metadata.__class__(forests=updated_forests)

    ctx.forest.save_forests(updated_metadata)

    user_output(
        f"  {click.style('✓', fg='green')} Forest "
        f"'{click.style(plan.forest_name, fg='cyan', bold=True)}' updated"
    )

    # Display results
    user_output()
    user_output(
        click.style("✅ Split complete!", fg="green")
        + f" Created {len(plan.branches_to_split)} new worktrees."
    )
