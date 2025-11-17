"""Current command implementation - displays current erk name."""

import click

from erk.cli.core import discover_repo_context
from erk.cli.json_output import emit_json
from erk.cli.json_schemas import CurrentCommandResponse
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_utils import find_current_worktree, is_root_worktree


@click.command("current", hidden=True)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output JSON format",
)
@click.pass_obj
def current_cmd(ctx: ErkContext, output_json: bool) -> None:
    """Show current erk name (hidden command for automation)."""
    # Use ctx.repo if it's a valid RepoContext, otherwise discover
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        # Discover repository context (handles None and NoRepoSentinel)
        # If not in a git repo, FileNotFoundError will bubble up
        repo = discover_repo_context(ctx, ctx.cwd)

    current_dir = ctx.cwd
    worktrees = ctx.git_ops.list_worktrees(repo.root)
    wt_info = find_current_worktree(worktrees, current_dir)

    if wt_info is None:
        raise SystemExit(1)

    # Determine name and is_root status
    is_root = is_root_worktree(wt_info.path, repo.root)
    name = "root" if is_root else wt_info.path.name

    # Output based on format
    if output_json:
        response = CurrentCommandResponse(
            name=name,
            path=str(wt_info.path),
            is_root=is_root,
        )
        emit_json(response.model_dump(mode="json"))
    else:
        user_output(name)
