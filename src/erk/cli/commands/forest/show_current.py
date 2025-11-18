"""Show current worktree's forest command."""

import click

from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.forest_utils import find_forest_by_worktree
from erk.core.repo_discovery import NoRepoSentinel
from erk.core.worktree_utils import find_current_worktree


@click.command("forest", help="Show forest for current worktree")
@click.pass_obj
def show_current_forest(ctx: ErkContext) -> None:
    """Show forest for current worktree.

    Displays the forest name and all worktrees in the forest,
    highlighting the current worktree.
    """
    if isinstance(ctx.repo, NoRepoSentinel):
        user_output(
            click.style("Error: ", fg="red")
            + "Not in a repository. This command requires a git repository."
        )
        raise SystemExit(1)

    # Get current worktree
    worktrees = ctx.git_ops.list_worktrees(ctx.repo.root)
    current_wt = find_current_worktree(worktrees, ctx.cwd)

    if current_wt is None:
        user_output("Current directory is not in an erk worktree.")
        raise SystemExit(1)

    # Extract worktree name from path
    worktree_name = current_wt.path.name

    # Load forests
    metadata = ctx.forest_ops.load_forests()

    # Find forest for current worktree
    forest = find_forest_by_worktree(metadata, worktree_name)

    if forest is None:
        user_output("Current worktree is not in a forest.")
        raise SystemExit(0)

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

        if wt == worktree_name:
            indicator = click.style(" ← you are here", fg="bright_green", bold=True)
            user_output(f"{prefix} {wt_display} {branch_display}{indicator}")
        else:
            user_output(f"{prefix} {wt_display} {branch_display}")
