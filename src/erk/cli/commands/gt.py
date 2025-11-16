"""Graphite integration commands for erk.

Provides machine-readable access to Graphite metadata for scripting and automation.
"""

import json
from dataclasses import asdict

import click

from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.tree_utils import format_branches_as_tree


@click.group("graphite")
@click.pass_obj
def graphite_group(ctx: ErkContext) -> None:
    """Graphite integration commands for machine-readable metadata.

    Requires use-graphite enabled.
    """
    pass


@graphite_group.command("branches")
@click.option(
    "--format",
    type=click.Choice(["text", "json", "tree"]),
    default="text",
    help="Output format (text, json, or tree)",
)
@click.option(
    "--stack",
    type=str,
    default=None,
    help="Show only this branch and its descendants (tree format only)",
)
@click.pass_obj
def graphite_branches_cmd(ctx: ErkContext, format: str, stack: str | None) -> None:
    """List all Graphite-tracked branches with machine-readable metadata.

    By default, outputs a simple list of branch names (one per line).
    Use --format json for structured output with full metadata.
    Use --format tree for hierarchical tree visualization.

    Examples:
        $ workstack graphite branches
        main
        feature-1
        feature-2

        $ workstack graphite branches --format json
        {
          "branches": [
            {
              "name": "main",
              "parent": null,
              "children": ["feature-1"],
              "is_trunk": true,
              "commit_sha": "abc123..."
            }
          ]
        }

        $ workstack graphite branches --format tree
        main (abc123f) "Initial commit"
        ├─ feature-a (def456g) "Add user authentication"
        │  └─ feature-a-tests (789hij0) "Add tests for auth"
        └─ feature-b (klm123n) "Refactor database layer"

        $ workstack graphite branches --format tree --stack feature-a
        feature-a (def456g) "Add user authentication"
        └─ feature-a-tests (789hij0) "Add tests for auth"

    Requires:
        - Graphite enabled (use_graphite config)
        - Valid .git/.graphite_cache_persist file
    """
    # Check if graphite is enabled
    if not (ctx.global_config and ctx.global_config.use_graphite):
        user_output(
            "Error: Graphite not enabled. Run 'erk config set use_graphite true'",
        )
        raise SystemExit(1)

    # Check if --stack is used without tree format
    if stack is not None and format != "tree":
        user_output(
            "Error: --stack option can only be used with --format tree",
        )
        raise SystemExit(1)

    # Discover repository
    repo = discover_repo_context(ctx, ctx.cwd)

    # Get branches from GraphiteOps
    branches_dict = ctx.graphite_ops.get_all_branches(ctx.git_ops, repo.root)

    if format == "json":
        # Convert to list of dicts for JSON output
        branches_list = [asdict(metadata) for metadata in branches_dict.values()]
        output = {"branches": branches_list}
        user_output(json.dumps(output, indent=2))
    elif format == "tree":
        # Tree format: hierarchical display with commit info
        # Collect commit messages for all branches
        commit_messages = {}
        for metadata in branches_dict.values():
            if metadata.commit_sha:
                msg = ctx.git_ops.get_commit_message(repo.root, metadata.commit_sha)
                if msg:
                    commit_messages[metadata.commit_sha] = msg

        output = format_branches_as_tree(branches_dict, commit_messages, root_branch=stack)
        user_output(output)
    else:
        # Text format: simple list of branch names
        for branch_name in sorted(branches_dict.keys()):
            user_output(branch_name)
