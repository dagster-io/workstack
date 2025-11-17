"""Tree visualization utilities for Graphite branches.

This module contains pure business logic for rendering Graphite branch
hierarchies as tree structures. These functions are used by the
`erk graphite branches --format tree` command.
"""

from erk.core.branch_metadata import BranchMetadata


def format_branches_as_tree(
    branches: dict[str, BranchMetadata],
    commit_messages: dict[str, str],
    *,
    root_branch: str | None,
) -> str:
    """Format branches as a hierarchical tree with commit info.

    Args:
        branches: Mapping of branch name to metadata
        commit_messages: Mapping of commit SHA to commit message
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
        format_branch_recursive(
            branch_name=root,
            branches=branches,
            commit_messages=commit_messages,
            lines=lines,
            prefix="",
            is_last=is_last_root,
            is_root=True,
        )

    return "\n".join(lines)


def format_branch_recursive(
    branch_name: str,
    branches: dict[str, BranchMetadata],
    commit_messages: dict[str, str],
    lines: list[str],
    prefix: str,
    is_last: bool,
    is_root: bool,
) -> None:
    """Recursively format a branch and its children with commit info.

    Args:
        branch_name: Name of current branch to format
        branches: All branches metadata
        commit_messages: Mapping of commit SHA to commit message
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
        commit_messages.get(metadata.commit_sha, "No commit message")
        if metadata.commit_sha
        else "No commit message"
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
            format_branch_recursive(
                branch_name=child,
                branches=branches,
                commit_messages=commit_messages,
                lines=lines,
                prefix=child_prefix,
                is_last=is_last_child,
                is_root=False,
            )
