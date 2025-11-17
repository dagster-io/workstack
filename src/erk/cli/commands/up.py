import click

from erk.cli.commands.navigation_helpers import (
    _activate_worktree,
    _ensure_graphite_enabled,
    _resolve_up_navigation,
)
from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.core.context import ErkContext


@click.command("up")
@click.option(
    "--script", is_flag=True, help="Print only the activation script without usage instructions."
)
@click.pass_obj
def up_cmd(ctx: ErkContext, script: bool) -> None:
    """Move to child branch in Graphite stack.

    With shell integration (recommended):
      erk up

    The shell wrapper function automatically activates the worktree.
    Run 'erk init --shell' to set up shell integration.

    Without shell integration:
      source <(erk up --script)

    This will cd to the child branch's worktree, create/activate .venv, and load .env variables.
    Requires Graphite to be enabled: 'erk config set use_graphite true'
    """
    _ensure_graphite_enabled(ctx)
    repo = discover_repo_context(ctx, ctx.cwd)

    # Get current branch
    current_branch = ctx.git_ops.get_current_branch(ctx.cwd)
    if current_branch is None:
        user_output("Error: Not currently on a branch (detached HEAD)")
        raise SystemExit(1)

    # Get all worktrees for checking if target has a worktree
    worktrees = ctx.git_ops.list_worktrees(repo.root)

    # Resolve navigation to get target branch (may auto-create worktree)
    target_name, was_created = _resolve_up_navigation(ctx, repo, current_branch, worktrees)

    # Show creation message if worktree was just created
    if was_created and not script:
        user_output(
            click.style("✓", fg="green")
            + f" Created worktree for {click.style(target_name, fg='yellow')} and moved to it"
        )

    # Resolve target branch to actual worktree path
    target_wt_path = ctx.git_ops.find_worktree_for_branch(repo.root, target_name)
    if target_wt_path is None:
        # This should not happen because _resolve_up_navigation already checks
        # But include defensive error handling
        user_output(
            f"Error: Branch '{target_name}' has no worktree. This should not happen.",
        )
        raise SystemExit(1)

    _activate_worktree(ctx, repo, target_wt_path, script, "up")
