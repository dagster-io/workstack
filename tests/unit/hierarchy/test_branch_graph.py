"""Unit tests for branch graph filtering and tree building logic.

These tests verify the pure business logic for:
- Filtering branch graphs to active branches
- Building tree structures from graphs
- Rendering tree output

These are unit tests (no CLI, no files) that were extracted from test_tree.py
to follow proper test layer discipline.
"""

from pathlib import Path

from workstack.core.tree_utils import (
    BranchGraph,
    TreeNode,
    WorktreeMapping,
    build_tree_from_graph,
    filter_graph_to_active_branches,
    render_tree,
)

# ===========================
# Graph Filtering Tests
# ===========================


def test_filter_graph_keeps_only_active_branches() -> None:
    """Test that graph filtering removes inactive branches."""
    graph = BranchGraph(
        parent_of={
            "feature-a": "main",
            "feature-b": "main",
            "feature-c": "feature-b",
        },
        children_of={
            "main": ["feature-a", "feature-b"],
            "feature-b": ["feature-c"],
            "feature-a": [],
            "feature-c": [],
        },
        trunk_branches=["main"],
    )

    # Only feature-a and main have worktrees
    active = {"main", "feature-a"}

    filtered = filter_graph_to_active_branches(graph, active)

    assert filtered.parent_of == {"feature-a": "main"}
    assert filtered.children_of == {"main": ["feature-a"]}
    assert filtered.trunk_branches == ["main"]


def test_filter_graph_preserves_multi_level_hierarchy() -> None:
    """Test filtering with nested branches."""
    graph = BranchGraph(
        parent_of={
            "child": "parent",
            "grandchild": "child",
        },
        children_of={
            "parent": ["child"],
            "child": ["grandchild"],
            "grandchild": [],
        },
        trunk_branches=["parent"],
    )

    # All branches are active
    active = {"parent", "child", "grandchild"}

    filtered = filter_graph_to_active_branches(graph, active)

    assert filtered.parent_of == {"child": "parent", "grandchild": "child"}
    assert filtered.children_of == {
        "parent": ["child"],
        "child": ["grandchild"],
    }
    assert filtered.trunk_branches == ["parent"]


# ===========================
# Tree Building Tests
# ===========================


def test_build_tree_creates_correct_structure() -> None:
    """Test tree building from graph."""
    graph = BranchGraph(
        parent_of={"feature-a": "main"},
        children_of={"main": ["feature-a"], "feature-a": []},
        trunk_branches=["main"],
    )

    mapping = WorktreeMapping(
        branch_to_worktree={"main": "root", "feature-a": "feature-a"},
        worktree_to_path={
            "root": Path("/repo"),
            "feature-a": Path("/repo/work/feature-a"),
        },
        current_worktree="root",
    )

    roots = build_tree_from_graph(graph, mapping)

    assert len(roots) == 1
    assert roots[0].branch_name == "main"
    assert roots[0].worktree_name == "root"
    assert roots[0].is_current is True
    assert len(roots[0].children) == 1
    assert roots[0].children[0].branch_name == "feature-a"
    assert roots[0].children[0].is_current is False


def test_build_tree_handles_multiple_children() -> None:
    """Test tree building with multiple children per parent."""
    graph = BranchGraph(
        parent_of={
            "feature-a": "main",
            "feature-b": "main",
        },
        children_of={
            "main": ["feature-a", "feature-b"],
            "feature-a": [],
            "feature-b": [],
        },
        trunk_branches=["main"],
    )

    mapping = WorktreeMapping(
        branch_to_worktree={
            "main": "root",
            "feature-a": "feature-a",
            "feature-b": "feature-b",
        },
        worktree_to_path={
            "root": Path("/repo"),
            "feature-a": Path("/repo/work/feature-a"),
            "feature-b": Path("/repo/work/feature-b"),
        },
        current_worktree=None,
    )

    roots = build_tree_from_graph(graph, mapping)

    assert len(roots) == 1
    assert roots[0].branch_name == "main"
    assert len(roots[0].children) == 2
    child_names = {child.branch_name for child in roots[0].children}
    assert child_names == {"feature-a", "feature-b"}


def test_build_tree_handles_multiple_trunk_branches() -> None:
    """Test tree building with multiple trunk branches (main, develop)."""
    graph = BranchGraph(
        parent_of={
            "feature-1": "main",
            "feature-2": "develop",
        },
        children_of={
            "main": ["feature-1"],
            "develop": ["feature-2"],
            "feature-1": [],
            "feature-2": [],
        },
        trunk_branches=["main", "develop"],
    )

    mapping = WorktreeMapping(
        branch_to_worktree={
            "main": "root",
            "develop": "develop",
            "feature-1": "feature-1",
            "feature-2": "feature-2",
        },
        worktree_to_path={
            "root": Path("/repo"),
            "develop": Path("/repo/work/develop"),
            "feature-1": Path("/repo/work/feature-1"),
            "feature-2": Path("/repo/work/feature-2"),
        },
        current_worktree="root",
    )

    roots = build_tree_from_graph(graph, mapping)

    # Should have two root nodes (main and develop)
    assert len(roots) == 2
    root_names = {root.branch_name for root in roots}
    assert root_names == {"main", "develop"}

    # Each root should have one child
    main_root = next(r for r in roots if r.branch_name == "main")
    develop_root = next(r for r in roots if r.branch_name == "develop")

    assert len(main_root.children) == 1
    assert main_root.children[0].branch_name == "feature-1"

    assert len(develop_root.children) == 1
    assert develop_root.children[0].branch_name == "feature-2"


# ===========================
# Tree Rendering Tests
# ===========================


def test_render_tree_single_branch() -> None:
    """Test rendering a single branch."""
    root = TreeNode(
        branch_name="main",
        worktree_name="root",
        children=[],
        is_current=False,
    )

    output = render_tree([root])

    # Should just show the branch with annotation, no tree characters
    assert "main" in output
    assert "[@root]" in output
    assert "├─" not in output
    assert "└─" not in output


def test_render_tree_with_children() -> None:
    """Test rendering tree with parent and children."""
    root = TreeNode(
        branch_name="main",
        worktree_name="root",
        children=[
            TreeNode("feature-a", "feature-a", [], False),
            TreeNode("feature-b", "feature-b", [], False),
        ],
        is_current=False,
    )

    output = render_tree([root])

    assert "main" in output
    assert "[@root]" in output
    assert "feature-a" in output
    assert "[@feature-a]" in output
    assert "feature-b" in output
    assert "[@feature-b]" in output
    # Should have branch and last-child connectors
    assert "├─" in output
    assert "└─" in output


def test_render_tree_nested_hierarchy() -> None:
    """Test rendering deeply nested tree."""
    root = TreeNode(
        branch_name="main",
        worktree_name="root",
        children=[
            TreeNode(
                branch_name="parent",
                worktree_name="parent",
                children=[
                    TreeNode("child", "child", [], False),
                ],
                is_current=False,
            ),
        ],
        is_current=False,
    )

    output = render_tree([root])

    assert "main" in output
    assert "[@root]" in output
    assert "parent" in output
    assert "[@parent]" in output
    assert "child" in output
    assert "[@child]" in output
    # Should have vertical continuation line
    assert "│" in output or "└─" in output


def test_render_tree_with_very_deep_nesting() -> None:
    """Test rendering with many levels of nesting."""
    # Create 5-level deep tree
    level5 = TreeNode("level-5", "level-5", [], False)
    level4 = TreeNode("level-4", "level-4", [level5], False)
    level3 = TreeNode("level-3", "level-3", [level4], False)
    level2 = TreeNode("level-2", "level-2", [level3], False)
    level1 = TreeNode("level-1", "level-1", [level2], False)
    root = TreeNode("main", "root", [level1], False)

    output = render_tree([root])

    # All levels should be present
    assert "main" in output
    assert "level-1" in output
    assert "level-2" in output
    assert "level-3" in output
    assert "level-4" in output
    assert "level-5" in output

    # Should have tree characters
    assert "└─" in output
    # Deep nesting should have vertical lines
    assert "│" in output or "  " in output  # Indentation or vertical lines
