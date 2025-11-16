"""Tree visualization for workstack.

This module provides the CLI orchestration layer for tree visualization.
Business logic has been extracted to workstack.core.tree_utils.
"""

from pathlib import Path

from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.tree_utils import (
    BranchGraph,
    TreeNode,
    WorktreeMapping,
    build_branch_graph_from_metadata,
    build_tree_from_graph,
    filter_graph_to_active_branches,
)


def build_workstack_tree(
    ctx: ErkContext,
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
        ctx: Erk context with git operations
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
        user_output(
            "Error: Graphite cache not found. The 'tree' command requires Graphite.\n"
            "Make sure Graphite is enabled: erk config set use-graphite true"
        )
        raise SystemExit(1)

    # Step 3: Filter graph to only branches with worktrees
    active_branches = set(worktree_mapping.branch_to_worktree.keys())
    filtered_graph = filter_graph_to_active_branches(branch_graph, active_branches)

    # Step 4: Build tree from filtered graph
    return build_tree_from_graph(filtered_graph, worktree_mapping)


def _get_worktree_mapping(
    ctx: ErkContext,
    repo_root: Path,
) -> WorktreeMapping:
    """Get mapping of branches to worktrees.

    Queries git for all worktrees and creates mappings between branches,
    worktree names, and filesystem paths. Detects the current worktree.

    Args:
        ctx: Erk context with git operations
        repo_root: Path to repository root

    Returns:
        WorktreeMapping with all active worktrees and their branches
    """
    worktrees = ctx.git_ops.list_worktrees(repo_root)
    current_path = ctx.cwd.resolve()

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
    ctx: ErkContext,
    repo_root: Path,
) -> BranchGraph | None:
    """Load branch graph from Graphite cache using GraphiteOps abstraction.

    Calls ctx.graphite_ops.get_all_branches() and transforms BranchMetadata
    into the BranchGraph structure needed for tree display.

    Args:
        ctx: Erk context with git operations
        repo_root: Path to repository root

    Returns:
        BranchGraph if cache exists and is valid, None otherwise
    """
    # Get all branches from GraphiteOps abstraction
    all_branches = ctx.graphite_ops.get_all_branches(ctx.git_ops, repo_root)
    if not all_branches:
        return None

    # Transform BranchMetadata -> BranchGraph structure using utility function
    return build_branch_graph_from_metadata(all_branches)
