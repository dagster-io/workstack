"""Current command implementation - displays current workstack name."""

from pathlib import Path

import click

from workstack.cli.core import discover_repo_context
from workstack.core.context import WorkstackContext


@click.command("current", hidden=True)
@click.pass_obj
def current_cmd(ctx: WorkstackContext) -> None:
    """Show current workstack name (hidden command for automation)."""
    # Discover repository context
    # This raises FileNotFoundError if not in a git repo
    try:
        repo = discover_repo_context(ctx, Path.cwd())
    except FileNotFoundError:
        # Not in a git repository - exit silently with error code
        raise SystemExit(1) from None

    current_dir = Path.cwd().resolve()

    # Find which worktree we're in
    worktrees = ctx.git_ops.list_worktrees(repo.root)

    for wt in worktrees:
        # Check path exists before resolution/comparison (LBYL pattern)
        if wt.path.exists():
            wt_path_resolved = wt.path.resolve()
            # Check if we're in this worktree
            if current_dir == wt_path_resolved or current_dir.is_relative_to(wt_path_resolved):
                # Determine if this is the root worktree
                if repo.root.exists():
                    repo_root_resolved = repo.root.resolve()
                    if wt_path_resolved == repo_root_resolved:
                        click.echo("root")
                        return

                # Non-root worktree - output the directory name
                click.echo(wt.path.name)
                return

    # Not in any worktree - exit silently with error code
    raise SystemExit(1)
