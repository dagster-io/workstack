"""Current command implementation - displays current erk name."""

import click
from erk_shared.output.output import user_output

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_utils import find_current_worktree, is_root_worktree


@click.command("current", hidden=True)
@click.pass_obj
def current_wt(ctx: ErkContext) -> None:
    """Show current worktree name (hidden command for automation)."""
    # Use ctx.repo if it's a valid RepoContext, otherwise discover
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        # Discover repository context (handles None and NoRepoSentinel)
        # If not in a git repo, FileNotFoundError will bubble up
        repo = discover_repo_context(ctx, ctx.cwd)

    current_dir = ctx.cwd
    worktrees = ctx.git.list_worktrees(repo.root)
    wt_info = find_current_worktree(worktrees, current_dir)

    if wt_info is None:
        raise SystemExit(1)

    if is_root_worktree(wt_info.path, repo.root):
        user_output("root")
    else:
        user_output(wt_info.path.name)
