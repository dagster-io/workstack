"""Tree visualization command for worktrees."""

import click

from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.cli.tree import build_worktree_tree
from erk.core.context import ErkContext
from erk.core.tree_utils import render_tree


@click.command("tree")
@click.pass_obj
def tree_cmd(ctx: ErkContext) -> None:
    """Display tree of worktrees with their dependencies.

    Shows ONLY branches that have active worktrees, organized
    by their Graphite parent-child relationships.

    Requires Graphite to be enabled and configured.

    Example:
        $ erk tree
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
    roots = build_worktree_tree(ctx, repo.root)

    if not roots:
        user_output("No worktrees found")
        raise SystemExit(1)

    # Render and display
    tree_output = render_tree(roots)
    user_output(tree_output)
