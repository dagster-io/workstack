"""Graphite integration commands for workstack.

Provides machine-readable access to Graphite metadata for scripting and automation.
"""

import json
from dataclasses import asdict
from pathlib import Path

import click

from workstack.cli.core import discover_repo_context
from workstack.core.branch_metadata import BranchMetadata
from workstack.core.context import GlobalConfigNotFound, WorkstackContext
from workstack.core.gitops import GitOps


@click.group("graphite")
@click.pass_obj
def graphite_group(ctx: WorkstackContext) -> None:
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
def graphite_branches_cmd(ctx: WorkstackContext, format: str, stack: str | None) -> None:
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
    if isinstance(ctx.global_config, GlobalConfigNotFound):
        click.echo(
            "Error: Global config not found. Run 'workstack init'",
            err=True,
        )
        raise SystemExit(1)

    if not ctx.global_config.use_graphite:
        click.echo(
            "Error: Graphite not enabled. Run 'workstack config set use_graphite true'",
            err=True,
        )
        raise SystemExit(1)

    # Check if --stack is used without tree format
    if stack is not None and format != "tree":
        click.echo(
            "Error: --stack option can only be used with --format tree",
            err=True,
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
        click.echo(json.dumps(output, indent=2))
    elif format == "tree":
        # Tree format: hierarchical display with commit info
        output = _format_branches_as_tree(branches_dict, ctx.git_ops, repo.root, root_branch=stack)
        click.echo(output)
    else:
        # Text format: simple list of branch names
        for branch_name in sorted(branches_dict.keys()):
            click.echo(branch_name)


def _format_branches_as_tree(
    branches: dict[str, BranchMetadata],
    git_ops: GitOps,
    repo_root: Path,
    *,
    root_branch: str | None,
) -> str:
    """Format branches as a hierarchical tree.

    Args:
        branches: Mapping of branch name to metadata
        git_ops: GitOps instance for retrieving commit messages
        repo_root: Repository root path
        root_branch: Optional branch to use as root (shows only this branch and descendants)

    Returns:
        Multi-line string with tree visualization
    """
    # Determine which branches to show as roots
    if root_branch is not None:
        # Filter to specific branch and its descendants
        if root_branch not in branches:
            return f"Error: Branch '{root_branch}' not found"
        roots = [root_branch]
    else:
        # Show all trunk branches (branches with no parent)
        roots = [name for name, meta in branches.items() if meta.is_trunk]

    if not roots:
        return "No branches found"

    # Build tree lines
    lines: list[str] = []
    for i, root in enumerate(roots):
        is_last_root = i == len(roots) - 1
        _format_branch_recursive(
            branch_name=root,
            branches=branches,
            git_ops=git_ops,
            repo_root=repo_root,
            lines=lines,
            prefix="",
            is_last=is_last_root,
            is_root=True,
        )

    return "\n".join(lines)


def _format_branch_recursive(
    branch_name: str,
    branches: dict[str, BranchMetadata],
    git_ops: GitOps,
    repo_root: Path,
    lines: list[str],
    prefix: str,
    is_last: bool,
    is_root: bool,
) -> None:
    """Recursively format a branch and its children.

    Args:
        branch_name: Name of current branch to format
        branches: All branches metadata
        git_ops: GitOps instance for retrieving commit messages
        repo_root: Repository root path
        lines: List to append formatted lines to
        prefix: Prefix string for indentation
        is_last: True if this is the last child of its parent
        is_root: True if this is a root node
    """
    if branch_name not in branches:
        return

    metadata = branches[branch_name]

    # Get commit info
    short_sha = metadata.commit_sha[:7] if metadata.commit_sha else "unknown"
    commit_message = (
        git_ops.get_commit_message(repo_root, metadata.commit_sha) or "No commit message"
    )

    # Format current line
    connector = "└─" if is_last else "├─"
    branch_info = f'{branch_name} ({short_sha}) "{commit_message}"'

    if is_root:
        # Root node: no connector
        line = branch_info
    else:
        # All other nodes get connectors
        line = f"{prefix}{connector} {branch_info}"

    lines.append(line)

    # Process children
    children = metadata.children
    if children:
        # Determine prefix for children
        if prefix:
            # Non-root node: extend existing prefix
            child_prefix = prefix + ("   " if is_last else "│  ")
        else:
            # Root node's children: start with appropriate spacing
            child_prefix = "   " if is_last else "│  "

        for i, child in enumerate(children):
            is_last_child = i == len(children) - 1
            _format_branch_recursive(
                branch_name=child,
                branches=branches,
                git_ops=git_ops,
                repo_root=repo_root,
                lines=lines,
                prefix=child_prefix,
                is_last=is_last_child,
                is_root=False,
            )
