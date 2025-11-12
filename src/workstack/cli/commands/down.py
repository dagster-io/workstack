import click

from workstack.cli.commands.switch import (
    _activate_root_repo,
    _activate_worktree,
    _ensure_graphite_enabled,
    _resolve_down_navigation,
)
from workstack.cli.core import discover_repo_context
from workstack.core.context import WorkstackContext, read_trunk_from_pyproject


@click.command("down")
@click.option(
    "--script", is_flag=True, help="Print only the activation script without usage instructions."
)
@click.pass_obj
def down_cmd(ctx: WorkstackContext, script: bool) -> None:
    """Move to parent branch in Graphite stack.

    With shell integration (recommended):
      workstack down

    The shell wrapper function automatically activates the worktree.
    Run 'workstack init --shell' to set up shell integration.

    Without shell integration:
      source <(workstack down --script)

    This will cd to the parent branch's worktree (or root repo if parent is trunk),
    create/activate .venv, and load .env variables.
    Requires Graphite to be enabled: 'workstack config set use_graphite true'
    """
    _ensure_graphite_enabled(ctx)
    repo = discover_repo_context(ctx, ctx.cwd)
    trunk_branch = read_trunk_from_pyproject(repo.root)

    # Get current branch
    current_branch = ctx.git_ops.get_current_branch(ctx.cwd)
    if current_branch is None:
        click.echo("Error: Not currently on a branch (detached HEAD)", err=True)
        raise SystemExit(1)

    # Get all worktrees for checking if target has a worktree
    worktrees = ctx.git_ops.list_worktrees(repo.root)

    # Resolve navigation to get target branch or 'root'
    target_name = _resolve_down_navigation(ctx, repo, current_branch, worktrees, trunk_branch)

    # Check if target_name refers to 'root' which means root repo
    if target_name == "root":
        _activate_root_repo(ctx, repo, script, "down")

    # Resolve target branch to actual worktree path
    target_wt_path = ctx.git_ops.find_worktree_for_branch(repo.root, target_name)
    if target_wt_path is None:
        # This should not happen because _resolve_down_navigation already checks
        # But include defensive error handling
        click.echo(
            f"Error: Branch '{target_name}' has no worktree. This should not happen.",
            err=True,
        )
        raise SystemExit(1)

    _activate_worktree(ctx, repo, target_wt_path, script, "down")
