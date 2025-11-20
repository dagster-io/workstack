"""Show specific forest command."""

import click

from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.forest_utils import find_forest_by_worktree
from erk.core.repo_discovery import NoRepoSentinel
from erk.core.worktree_utils import find_current_worktree


@click.command("show", help="Show details of a specific forest")
@click.argument("name", required=False)
@click.pass_obj
def show_forest(ctx: ErkContext, name: str | None) -> None:
    """Show details of a specific forest.

    If name is not provided, shows the forest for the current worktree.

    Args:
        name: Optional forest name to show
    """
    if isinstance(ctx.repo, NoRepoSentinel):
        user_output(
            click.style("Error: ", fg="red")
            + "Not in a repository. This command requires a git repository."
        )
        raise SystemExit(1)

    # Load forests
    metadata = ctx.forest.load_forests()

    # Determine which forest to show
    if name is None:
        # Default to current worktree's forest
        worktrees = ctx.git.list_worktrees(ctx.repo.root)
        current_wt_info = find_current_worktree(worktrees, ctx.cwd)

        if current_wt_info is None:
            user_output(
                click.style("Error: ", fg="red")
                + "Not in a worktree and no forest name provided.\n\n"
                + "Usage: erk forest show [NAME]"
            )
            raise SystemExit(1)

        worktree_name = current_wt_info.path.name
        forest = find_forest_by_worktree(metadata, worktree_name)

        if forest is None:
            user_output(
                click.style("Error: ", fg="red")
                + "Current worktree is not in a forest.\n\n"
                + "Use 'erk forest list' to see all forests."
            )
            raise SystemExit(1)

        current_worktree = worktree_name
    else:
        # Show specified forest
        if name not in metadata.forests:
            available = ", ".join(metadata.forests.keys()) if metadata.forests else "(none)"
            user_output(
                click.style("❌ Error: ", fg="red")
                + f"Forest '{name}' not found\n\n"
                + f"Available forests: {available}"
            )
            raise SystemExit(1)

        forest = metadata.forests[name]

        # Try to determine current worktree
        worktrees = ctx.git.list_worktrees(ctx.repo.root)
        current_wt_info = find_current_worktree(worktrees, ctx.cwd)
        current_worktree = (
            current_wt_info.path.name
            if current_wt_info and current_wt_info.path.name in forest.worktrees
            else None
        )

    # Display forest
    forest_header = click.style(f"Forest: {forest.name}", fg="cyan", bold=True)
    count_text = f" ({len(forest.worktrees)} worktrees)"
    user_output(forest_header + count_text)

    # Display worktrees in tree format
    for idx, wt in enumerate(forest.worktrees):
        is_last = idx == len(forest.worktrees) - 1
        prefix = "└──" if is_last else "├──"

        # Highlight current worktree
        wt_display = click.style(wt, fg="yellow")
        branch_display = f"[{wt}]"

        if wt == current_worktree:
            indicator = click.style(" ← you are here", fg="bright_green", bold=True)
            user_output(f"{prefix} {wt_display} {branch_display}{indicator}")
        else:
            user_output(f"{prefix} {wt_display} {branch_display}")
