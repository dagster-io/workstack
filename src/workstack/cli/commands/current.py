"""Current command implementation - displays current workstack name."""

import click

from workstack.cli.core import discover_repo_context
from workstack.core.context import WorkstackContext
from workstack.core.worktree_utils import find_current_worktree, is_root_worktree


@click.command("current", hidden=True)
@click.pass_obj
def current_cmd(ctx: WorkstackContext) -> None:
    """Show current workstack name (hidden command for automation)."""
    # Discover repository context
    # This raises FileNotFoundError if not in a git repo
    try:
        repo = discover_repo_context(ctx, ctx.cwd)
    except FileNotFoundError:
        # Not in a git repository - exit silently with error code
        raise SystemExit(1) from None

    current_dir = ctx.cwd.resolve()
    worktrees = ctx.git_ops.list_worktrees(repo.root)
    wt_info = find_current_worktree(worktrees, current_dir)

    if wt_info is None:
        raise SystemExit(1)

    if is_root_worktree(wt_info.path, repo.root):
        click.echo("root")
    else:
        click.echo(wt_info.path.name)
