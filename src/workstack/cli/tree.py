"""Tree visualization for workstack.

This module builds and renders tree structures showing worktrees and their
Graphite dependency relationships. All functions are pure (no I/O) except
for the entry point which loads data via WorkstackContext.
"""

from dataclasses import dataclass
from pathlib import Path

import click

from workstack.core.context import WorkstackContext
from workstack.core.graphite_ops import read_graphite_json_file


@dataclass(frozen=True)
class TreeNode:
    """A node in the workstack tree.

    Represents a branch in the tree, which may or may not have an active worktree.
    Branches without worktrees are included when they are trunk branches or
    intermediate parents connecting worktree branches to trunks.

    Attributes:
        branch_name: Git branch name (e.g., "fix-workstack-s")
        worktree_name: Worktree directory name (e.g., "root", "fix-plan"), or None if no worktree
        children: List of child TreeNode objects
        is_current: True if this worktree is the current working directory
    """

    branch_name: str
    worktree_name: str | None
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


def build_workstack_tree(
    ctx: WorkstackContext,
    repo_root: Path,
) -> list[TreeNode]:
    """Build tree structure of ONLY branches with active worktrees.

    This is the main entry point that orchestrates the tree building process:
    1. Get all worktrees and their branches from git
    2. Load Graphite cache for parent-child relationships (REQUIRED)
    3. Build branch graph from cache data
    4. Filter graph to ONLY branches that have worktrees
    5. Build tree starting from trunk branches
    6. Return list of root nodes (typically just "main")

    Args:
        ctx: Workstack context with git operations
        repo_root: Path to repository root

    Returns:
        List of root TreeNode objects (typically one for trunk)

    Raises:
        SystemExit: If Graphite cache doesn't exist or can't be loaded
    """
    # Step 1: Get worktrees
    worktree_mapping = _get_worktree_mapping(ctx, repo_root)

    # Step 2: Load Graphite cache (REQUIRED - hard fail if missing)
    branch_graph = _load_graphite_branch_graph(ctx, repo_root)
    if branch_graph is None:
        click.echo(
            "Error: Graphite cache not found. The 'tree' command requires Graphite.\n"
            "Make sure Graphite is enabled: workstack config set use-graphite true",
            err=True,
        )
        raise SystemExit(1)

    # Step 3: Filter graph to only branches with worktrees
    active_branches = set(worktree_mapping.branch_to_worktree.keys())
    filtered_graph = _filter_graph_to_active_branches(branch_graph, active_branches)

    # Step 4: Build tree from filtered graph
    return _build_tree_from_graph(filtered_graph, worktree_mapping)


def _get_worktree_mapping(
    ctx: WorkstackContext,
    repo_root: Path,
) -> WorktreeMapping:
    """Get mapping of branches to worktrees.

    Queries git for all worktrees and creates mappings between branches,
    worktree names, and filesystem paths. Detects the current worktree.

    Args:
        ctx: Workstack context with git operations
        repo_root: Path to repository root

    Returns:
        WorktreeMapping with all active worktrees and their branches
    """
    worktrees = ctx.git_ops.list_worktrees(repo_root)
    current_path = Path.cwd().resolve()

    branch_to_worktree: dict[str, str] = {}
    worktree_to_path: dict[str, Path] = {}
    current_worktree: str | None = None

    for wt in worktrees:
        # Skip worktrees with detached HEAD
        if wt.branch is None:
            continue

        # Determine worktree name
        if wt.path.resolve() == repo_root.resolve():
            worktree_name = "root"
        else:
            # Use directory name from workstack's work directory
            worktree_name = wt.path.name

        branch_to_worktree[wt.branch] = worktree_name
        worktree_to_path[worktree_name] = wt.path

        # Check if current path is within this worktree (handles subdirectories)
        try:
            current_path.relative_to(wt.path.resolve())
            current_worktree = worktree_name
        except ValueError:
            # Not within this worktree
            pass

    return WorktreeMapping(
        branch_to_worktree=branch_to_worktree,
        worktree_to_path=worktree_to_path,
        current_worktree=current_worktree,
    )


def _load_graphite_branch_graph(
    ctx: WorkstackContext,
    repo_root: Path,
) -> BranchGraph | None:
    """Load branch graph from Graphite cache.

    Reads .git/.graphite_cache_persist JSON file and extracts parent-child
    relationships between branches.

    Args:
        ctx: Workstack context with git operations
        repo_root: Path to repository root

    Returns:
        BranchGraph if cache exists and is valid, None otherwise
    """
    # Get git common directory (handles both main repos and worktrees)
    git_dir = ctx.git_ops.get_git_common_dir(repo_root)
    if git_dir is None:
        return None

    # Check if Graphite cache file exists and parse
    cache_file = git_dir / ".graphite_cache_persist"
    if not cache_file.exists():
        return None

    cache_data = read_graphite_json_file(cache_file, "Graphite cache")

    branches_data = cache_data.get("branches", [])

    # Build relationship maps
    parent_of: dict[str, str] = {}
    children_of: dict[str, list[str]] = {}
    trunk_branches: list[str] = []

    for branch_name, info in branches_data:
        parent = info.get("parentBranchName")
        children = info.get("children", [])
        is_trunk = info.get("validationResult") == "TRUNK"

        # Record parent relationship
        if parent:
            parent_of[branch_name] = parent

        # Record children
        children_of[branch_name] = children

        # Record trunk branches
        if is_trunk or parent is None:
            trunk_branches.append(branch_name)

    return BranchGraph(
        parent_of=parent_of,
        children_of=children_of,
        trunk_branches=trunk_branches,
    )


def _filter_graph_to_active_branches(
    graph: BranchGraph,
    active_branches: set[str],
) -> BranchGraph:
    """Filter branch graph to include branches with worktrees and their ancestors.

    This keeps:
    1. All branches with active worktrees
    2. All trunk branches (even without worktrees) to serve as roots
    3. All intermediate parent branches needed to connect worktrees to trunks

    Only removes branches that have no worktrees AND no descendants with worktrees.

    Args:
        graph: Full branch graph from Graphite cache
        active_branches: Set of branch names that have worktrees

    Returns:
        Filtered BranchGraph containing active branches and their connecting ancestors

    Example:
        Input graph: main -> [feature-a, feature-b -> feature-b-2]
        Active branches: {feature-a}  (main has no worktree)
        Output graph: main -> [feature-a]
        (main is kept as trunk, feature-b and feature-b-2 are removed)
    """
    # Start with branches that have worktrees
    branches_to_keep: set[str] = set(active_branches)

    # Add all trunk branches (needed as roots even without worktrees)
    branches_to_keep.update(graph.trunk_branches)

    # Add all intermediate parents to connect active branches to trunks
    for branch in active_branches:
        current = branch
        while current in graph.parent_of:
            parent = graph.parent_of[current]
            branches_to_keep.add(parent)
            current = parent

    # Build filtered graph from branches to keep
    filtered_parent_of: dict[str, str] = {}
    filtered_children_of: dict[str, list[str]] = {}
    filtered_trunk: list[str] = []

    for branch in branches_to_keep:
        # Keep parent relationship if branch and parent are both kept
        if branch in graph.parent_of:
            parent = graph.parent_of[branch]
            if parent in branches_to_keep:
                filtered_parent_of[branch] = parent

        # Keep only children that are also kept
        if branch in graph.children_of:
            kept_children = [
                child for child in graph.children_of[branch] if child in branches_to_keep
            ]
            if kept_children:
                filtered_children_of[branch] = kept_children

        # Keep trunk status if this branch is a trunk
        if branch in graph.trunk_branches:
            filtered_trunk.append(branch)

    return BranchGraph(
        parent_of=filtered_parent_of,
        children_of=filtered_children_of,
        trunk_branches=filtered_trunk,
    )


def _build_tree_from_graph(
    graph: BranchGraph,
    mapping: WorktreeMapping,
) -> list[TreeNode]:
    """Build TreeNode structure from filtered branch graph.

    Recursively builds tree nodes starting from trunk branches, following
    parent-child relationships to create the full tree structure.

    Handles branches both with and without worktrees (branches without worktrees
    are included when they are trunks or intermediate parents).

    Args:
        graph: Filtered graph containing branches with worktrees and their ancestors
        mapping: Worktree mapping for annotations

    Returns:
        List of root TreeNode objects (one per trunk branch)
    """

    def build_node(branch: str) -> TreeNode:
        """Recursively build a tree node and its children."""
        # Check if this branch has a worktree (LBYL pattern)
        if branch in mapping.branch_to_worktree:
            worktree_name = mapping.branch_to_worktree[branch]
            is_current = worktree_name == mapping.current_worktree
        else:
            # Branch has no worktree (trunk or intermediate parent)
            worktree_name = None
            is_current = False

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
        branch_text = _format_branch_name(node.branch_name, node.is_current)
        worktree_text = _format_worktree_annotation(node.worktree_name)

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


def _format_branch_name(branch: str, is_current: bool) -> str:
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


def _format_worktree_annotation(worktree_name: str | None) -> str:
    """Format worktree annotation [@name] or [no worktree].

    Args:
        worktree_name: Name of the worktree, or None if branch has no worktree

    Returns:
        Dimmed annotation text
    """
    if worktree_name is None:
        return click.style("[no worktree]", fg="bright_black")
    else:
        return click.style(f"[@{worktree_name}]", fg="bright_black")
