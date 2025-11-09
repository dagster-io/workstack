"""Tree visualization command for workstack."""

import click

from workstack.cli.core import discover_repo_context
from workstack.cli.tree import build_workstack_tree, render_tree
from workstack.core.context import WorkstackContext


@click.command("tree")
@click.pass_obj
def tree_cmd(ctx: WorkstackContext) -> None:
    """Display tree of worktrees with their dependencies.

    Shows ONLY branches that have active worktrees, organized
    by their Graphite parent-child relationships.

    Requires Graphite to be enabled and configured.

    Example:
        $ workstack tree
        main [@root]
        ├─ feature-a [@feature-a]
        │  └─ feature-a-2 [@feature-a-2]
        └─ feature-b [@feature-b]

    Legend:
        [@worktree-name] = worktree directory name
        Current worktree is highlighted in bright green
    """
    repo = discover_repo_context(ctx, ctx.cwd)

    # Build tree structure (will exit with error if Graphite cache missing)
    roots = build_workstack_tree(ctx, repo.root)

    if not roots:
        click.echo("No worktrees found", err=True)
        raise SystemExit(1)

    # Render and display
    tree_output = render_tree(roots)
    click.echo(tree_output)
