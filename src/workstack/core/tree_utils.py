"""Tree visualization utilities for workstack.

This module contains pure business logic for building and rendering tree structures
showing worktrees and their Graphite dependency relationships. All functions are
pure (no I/O) and can be tested without filesystem access.
"""

from dataclasses import dataclass
from pathlib import Path

import click

from workstack.core.branch_metadata import BranchMetadata


@dataclass(frozen=True)
class TreeNode:
    """A node in the workstack tree.

    Represents a branch that has an active worktree, with its children
    (dependent branches that also have worktrees).

    Attributes:
        branch_name: Git branch name (e.g., "fix-workstack-s")
        worktree_name: Worktree directory name (e.g., "root", "fix-plan")
        children: List of child TreeNode objects
        is_current: True if this worktree is the current working directory
    """

    branch_name: str
    worktree_name: str
    children: list["TreeNode"]
    is_current: bool


@dataclass(frozen=True)
class WorktreeMapping:
    """Mapping between branches and their worktrees.

    Attributes:
        branch_to_worktree: Map of branch name -> worktree name
        worktree_to_path: Map of worktree name -> filesystem path
        current_worktree: Name of current worktree (None if not in a worktree)
    """

    branch_to_worktree: dict[str, str]
    worktree_to_path: dict[str, Path]
    current_worktree: str | None


@dataclass(frozen=True)
class BranchGraph:
    """Graph of branch relationships from Graphite cache.

    Attributes:
        parent_of: Map of branch name -> parent branch name
        children_of: Map of branch name -> list of child branch names
        trunk_branches: List of trunk branch names (branches with no parent)
    """

    parent_of: dict[str, str]
    children_of: dict[str, list[str]]
    trunk_branches: list[str]


def build_branch_graph_from_metadata(
    all_branches: dict[str, BranchMetadata],
) -> BranchGraph:
    """Transform BranchMetadata dictionary into BranchGraph structure.

    Args:
        all_branches: Dictionary mapping branch names to their metadata

    Returns:
        BranchGraph with parent/child relationships extracted
    """
    parent_of: dict[str, str] = {}
    children_of: dict[str, list[str]] = {}
    trunk_branches: list[str] = []

    for branch_name, metadata in all_branches.items():
        # Record parent relationship
        if metadata.parent:
            parent_of[branch_name] = metadata.parent

        # Record children
        children_of[branch_name] = metadata.children

        # Record trunk branches
        if metadata.is_trunk:
            trunk_branches.append(branch_name)

    return BranchGraph(
        parent_of=parent_of,
        children_of=children_of,
        trunk_branches=trunk_branches,
    )


def filter_graph_to_active_branches(
    graph: BranchGraph,
    active_branches: set[str],
) -> BranchGraph:
    """Filter branch graph to ONLY include branches with active worktrees.

    This removes branches without worktrees from the graph while preserving
    the tree structure. Only active branches and their relationships are kept.

    Args:
        graph: Full branch graph from Graphite cache
        active_branches: Set of branch names that have worktrees

    Returns:
        Filtered BranchGraph containing only active branches

    Example:
        Input graph: main -> [feature-a, feature-b -> feature-b-2]
        Active branches: {main, feature-a}
        Output graph: main -> [feature-a]
        (feature-b and feature-b-2 are removed)
    """
    filtered_parent_of: dict[str, str] = {}
    filtered_children_of: dict[str, list[str]] = {}
    filtered_trunk: list[str] = []

    for branch in active_branches:
        # Keep parent relationship only if parent also has a worktree
        if branch in graph.parent_of:
            parent = graph.parent_of[branch]
            if parent in active_branches:
                # Parent has worktree - keep the relationship
                filtered_parent_of[branch] = parent
            else:
                # Parent has no worktree - promote this branch to trunk
                filtered_trunk.append(branch)

        # Keep only children that are also active
        if branch in graph.children_of:
            active_children = [
                child for child in graph.children_of[branch] if child in active_branches
            ]
            if active_children:
                filtered_children_of[branch] = active_children

        # Keep trunk status if active and not already added
        if branch in graph.trunk_branches and branch not in filtered_trunk:
            filtered_trunk.append(branch)

    return BranchGraph(
        parent_of=filtered_parent_of,
        children_of=filtered_children_of,
        trunk_branches=filtered_trunk,
    )


def build_tree_from_graph(
    graph: BranchGraph,
    mapping: WorktreeMapping,
) -> list[TreeNode]:
    """Build TreeNode structure from filtered branch graph.

    Recursively builds tree nodes starting from trunk branches, following
    parent-child relationships to create the full tree structure.

    Args:
        graph: Filtered graph containing only active branches
        mapping: Worktree mapping for annotations

    Returns:
        List of root TreeNode objects (one per trunk branch)
    """

    def build_node(branch: str) -> TreeNode:
        """Recursively build a tree node and its children."""
        worktree_name = mapping.branch_to_worktree[branch]
        is_current = worktree_name == mapping.current_worktree

        # Recursively build children
        children_branches = graph.children_of.get(branch, [])
        children = [build_node(child) for child in children_branches]

        return TreeNode(
            branch_name=branch,
            worktree_name=worktree_name,
            children=children,
            is_current=is_current,
        )

    # Build tree starting from trunk branches
    return [build_node(trunk) for trunk in graph.trunk_branches]


def render_tree(roots: list[TreeNode]) -> str:
    """Render tree structure as ASCII art with Unicode box-drawing characters.

    Uses Unicode box-drawing characters:
    - ├─ for middle children (branch continues below)
    - └─ for last child (no more branches below)
    - │  for continuation lines (shows vertical connection)

    Args:
        roots: List of root TreeNode objects

    Returns:
        Multi-line string with rendered tree

    Example:
        Input:
            TreeNode("main", "root", [
                TreeNode("feature-a", "feature-a", []),
                TreeNode("feature-b", "feature-b", [])
            ])

        Output:
            main [@root]
            ├─ feature-a [@feature-a]
            └─ feature-b [@feature-b]
    """
    lines: list[str] = []

    def render_node(node: TreeNode, prefix: str, is_last: bool, is_root: bool) -> None:
        """Recursively render a node and its children.

        Args:
            node: TreeNode to render
            prefix: Prefix string for indentation (contains │ and spaces)
            is_last: True if this is the last child of its parent
            is_root: True if this is a top-level root node
        """
        # Format current line
        connector = "└─" if is_last else "├─"
        branch_text = format_branch_name(node.branch_name, node.is_current)
        worktree_text = format_worktree_annotation(node.worktree_name)

        if is_root:
            # Root node: no connector
            line = f"{branch_text} {worktree_text}"
        else:
            # All other nodes get connectors
            line = f"{prefix}{connector} {branch_text} {worktree_text}"

        lines.append(line)

        # Render children
        if node.children:
            # Determine prefix for children
            # Build prefix based on whether this node is the last child of its parent
            if prefix:
                # Non-root node: extend existing prefix
                # Add vertical bar if more siblings below, space otherwise
                child_prefix = prefix + ("   " if is_last else "│  ")
            else:
                # Root node's children: start with appropriate spacing
                # Use spaces if this is last root, vertical bar otherwise
                child_prefix = "   " if is_last else "│  "

            for i, child in enumerate(node.children):
                is_last_child = i == len(node.children) - 1
                render_node(child, child_prefix, is_last_child, is_root=False)

    # Render all roots
    for i, root in enumerate(roots):
        is_last_root = i == len(roots) - 1
        render_node(root, "", is_last_root, is_root=True)

    return "\n".join(lines)


def format_branch_name(branch: str, is_current: bool) -> str:
    """Format branch name with color.

    Args:
        branch: Branch name to format
        is_current: True if this is the current worktree

    Returns:
        Colored branch name (bright green if current, normal otherwise)
    """
    if is_current:
        return click.style(branch, fg="bright_green", bold=True)
    else:
        return branch


def format_worktree_annotation(worktree_name: str) -> str:
    """Format worktree annotation [@name].

    Args:
        worktree_name: Name of the worktree

    Returns:
        Dimmed annotation text
    """
    return click.style(f"[@{worktree_name}]", fg="bright_black")


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
