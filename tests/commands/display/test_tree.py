"""Tests for workstack tree command.

This file tests CLI-specific behavior: command execution, error handling, and output formatting.
Pure business logic (graph filtering, tree building, rendering) is tested in
tests/unit/hierarchy/test_branch_graph.py.
"""

from pathlib import Path

from click.testing import CliRunner

from tests.fakes.context import create_test_context
from tests.fakes.gitops import FakeGitOps, WorktreeInfo
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.test_utils import sentinel_path
from tests.test_utils.env_helpers import pure_workstack_env
from workstack.cli.cli import cli
from workstack.cli.tree import (
    _get_worktree_mapping,
    _load_graphite_branch_graph,
)
from workstack.core.branch_metadata import BranchMetadata

# ===========================
# Helper Function Tests
# ===========================


def test_get_worktree_mapping() -> None:
    """Test worktree mapping creation from git worktrees."""
    repo_root = sentinel_path()
    workstacks_dir = sentinel_path() / "work"

    git_ops = FakeGitOps(
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main"),
                WorktreeInfo(path=workstacks_dir / "feature-a", branch="feature-a"),
                WorktreeInfo(path=workstacks_dir / "feature-b", branch="feature-b"),
            ]
        },
        current_branches={repo_root: "main"},
    )

    ctx = create_test_context(git_ops=git_ops, cwd=repo_root)

    mapping = _get_worktree_mapping(ctx, repo_root)

    assert mapping.branch_to_worktree == {
        "main": "root",
        "feature-a": "feature-a",
        "feature-b": "feature-b",
    }
    assert "root" in mapping.worktree_to_path
    assert mapping.current_worktree == "root"


def test_get_worktree_mapping_skips_detached_head() -> None:
    """Test that worktrees with detached HEAD are skipped."""
    repo_root = sentinel_path()

    git_ops = FakeGitOps(
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main"),
                WorktreeInfo(path=sentinel_path() / "work" / "detached", branch=None),
            ]
        },
    )

    ctx = create_test_context(git_ops=git_ops, cwd=repo_root)

    mapping = _get_worktree_mapping(ctx, repo_root)

    # Should only have main, not the detached HEAD worktree
    assert mapping.branch_to_worktree == {"main": "root"}


def test_get_worktree_mapping_detects_current_from_subdirectory() -> None:
    """Test that current worktree is detected when cwd is a subdirectory."""
    repo_root = sentinel_path()
    feature_worktree = Path("/repo/work/feature-a")
    subdirectory = feature_worktree / "src" / "module"

    git_ops = FakeGitOps(
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main"),
                WorktreeInfo(path=feature_worktree, branch="feature-a"),
            ]
        },
    )

    ctx = create_test_context(git_ops=git_ops, cwd=subdirectory)

    mapping = _get_worktree_mapping(ctx, repo_root)

    # Should detect feature-a as current even though cwd is in subdirectory
    assert mapping.current_worktree == "feature-a"


def test_get_worktree_mapping_handles_user_outside_all_worktrees() -> None:
    """Test behavior when user is not in any worktree."""
    repo_root = sentinel_path()
    outside_path = Path("/completely/different/path")

    git_ops = FakeGitOps(
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main"),
                WorktreeInfo(path=repo_root / "work" / "feature-a", branch="feature-a"),
            ]
        },
    )

    ctx = create_test_context(git_ops=git_ops, cwd=outside_path)

    mapping = _get_worktree_mapping(ctx, repo_root)

    # Should have no current worktree
    assert mapping.current_worktree is None


def test_load_graphite_branch_graph() -> None:
    """Test loading branch graph from Graphite cache."""
    repo_root = sentinel_path()

    # Create branch metadata matching the expected graph structure
    branches = {
        "main": BranchMetadata.trunk("main", children=["feature-a", "feature-b"]),
        "feature-a": BranchMetadata.branch("feature-a", parent="main"),
        "feature-b": BranchMetadata.branch("feature-b", parent="main", children=["feature-b-2"]),
        "feature-b-2": BranchMetadata.branch("feature-b-2", parent="feature-b"),
    }

    git_ops = FakeGitOps()
    graphite_ops = FakeGraphiteOps(branches=branches)
    ctx = create_test_context(git_ops=git_ops, graphite_ops=graphite_ops)

    graph = _load_graphite_branch_graph(ctx, repo_root)

    assert graph is not None
    assert graph.trunk_branches == ["main"]
    assert graph.parent_of == {
        "feature-a": "main",
        "feature-b": "main",
        "feature-b-2": "feature-b",
    }
    assert graph.children_of == {
        "main": ["feature-a", "feature-b"],
        "feature-a": [],
        "feature-b": ["feature-b-2"],
        "feature-b-2": [],
    }


def test_load_graphite_branch_graph_returns_none_when_missing() -> None:
    """Test that missing cache returns None."""
    repo_root = sentinel_path()

    # FakeGraphiteOps with empty branches dict simulates missing cache
    git_ops = FakeGitOps()
    graphite_ops = FakeGraphiteOps(branches={})
    ctx = create_test_context(git_ops=git_ops, graphite_ops=graphite_ops)

    graph = _load_graphite_branch_graph(ctx, repo_root)

    assert graph is None


# ===========================
# CLI Command Tests
# ===========================


def test_tree_command_displays_hierarchy() -> None:
    """Test that tree command shows worktree hierarchy."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        repo_root = env.cwd

        # Create branch metadata for FakeGraphiteOps
        branches = {
            "main": BranchMetadata.trunk("main", children=["feature-a"]),
            "feature-a": BranchMetadata.branch("feature-a", parent="main"),
        }

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(
                        path=env.workstacks_root / "feature-a",
                        branch="feature-a",
                    ),
                ]
            },
            current_branches={repo_root: "main"},
        )

        graphite_ops = FakeGraphiteOps(branches=branches)

        ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=graphite_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["tree"], obj=ctx)

        assert result.exit_code == 0
        assert "main" in result.output
        assert "[@root]" in result.output
        assert "feature-a" in result.output
        assert "[@feature-a]" in result.output
        # Check for tree characters
        assert "└─" in result.output or "├─" in result.output


def test_tree_command_filters_branches_without_worktrees() -> None:
    """Test that branches without worktrees are not shown.

    This verifies the CLI integration: the tree command should filter the graph
    before rendering to show only branches with active worktrees.
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        repo_root = env.cwd

        # Create branch metadata - 3 branches, but only 2 have worktrees
        branches = {
            "main": BranchMetadata.trunk("main", children=["feature-a", "feature-b"]),
            "feature-a": BranchMetadata.branch("feature-a", parent="main"),
            "feature-b": BranchMetadata.branch("feature-b", parent="main"),
        }

        # Only main and feature-a have worktrees (feature-b does not)
        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(
                        path=env.workstacks_root / "feature-a",
                        branch="feature-a",
                    ),
                ]
            },
        )

        graphite_ops = FakeGraphiteOps(branches=branches)

        ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=graphite_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["tree"], obj=ctx)

        assert result.exit_code == 0
        assert "main" in result.output
        assert "feature-a" in result.output
        # feature-b should NOT appear (no worktree)
        assert "feature-b" not in result.output


def test_tree_command_fails_without_graphite_cache() -> None:
    """Test that tree command fails gracefully when Graphite cache is missing."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        repo_root = env.cwd

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ]
            },
        )

        # Empty branches dict simulates missing cache
        graphite_ops = FakeGraphiteOps(branches={})

        ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=graphite_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["tree"], obj=ctx)

        assert result.exit_code == 1
        assert "Graphite cache not found" in result.output
        assert "tree' command requires Graphite" in result.output


def test_tree_command_shows_nested_hierarchy() -> None:
    """Test tree command with 3-level nested hierarchy."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        repo_root = env.cwd

        # Create 3-level branch hierarchy
        branches = {
            "main": BranchMetadata.trunk("main", children=["parent"]),
            "parent": BranchMetadata.branch("parent", parent="main", children=["child"]),
            "child": BranchMetadata.branch("child", parent="parent"),
        }

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=env.workstacks_root / "parent", branch="parent"),
                    WorktreeInfo(path=env.workstacks_root / "child", branch="child"),
                ]
            },
        )

        graphite_ops = FakeGraphiteOps(branches=branches)

        ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=graphite_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["tree"], obj=ctx)

        assert result.exit_code == 0
        assert "main" in result.output
        assert "parent" in result.output
        assert "child" in result.output
        # Should have vertical continuation for nested structure
        assert "│" in result.output or "└─" in result.output


def test_tree_command_shows_three_level_hierarchy_with_correct_indentation() -> None:
    """Test tree command displays 3-level stack with proper indentation.

    Reproduces bug where workstack-dev-cli-implementation and
    create-agents-symlinks-implementation-plan appear at same level
    instead of nested hierarchy.
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        repo_root = env.cwd

        # Setup 3-level stack matching the real bug scenario
        branches = {
            "main": BranchMetadata.trunk("main", children=["workstack-dev-cli-implementation"]),
            "workstack-dev-cli-implementation": BranchMetadata.branch(
                "workstack-dev-cli-implementation",
                parent="main",
                children=["create-agents-symlinks-implementation-plan"],
            ),
            "create-agents-symlinks-implementation-plan": BranchMetadata.branch(
                "create-agents-symlinks-implementation-plan",
                parent="workstack-dev-cli-implementation",
            ),
        }

        # All 3 branches have active worktrees
        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(
                        path=env.workstacks_root / "workstack-dev-cli-implementation",
                        branch="workstack-dev-cli-implementation",
                    ),
                    WorktreeInfo(
                        path=env.workstacks_root / "create-agents-symlinks-implementation-plan",
                        branch="create-agents-symlinks-implementation-plan",
                    ),
                ]
            },
            current_branches={repo_root: "main"},
        )

        graphite_ops = FakeGraphiteOps(branches=branches)

        ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=graphite_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["tree"], obj=ctx)

        assert result.exit_code == 0

        # Verify the exact structure with proper indentation
        # Expected:
        # main [@root]
        # └─ workstack-dev-cli-implementation [@workstack-dev-cli-implementation]
        #    └─ create-agents-symlinks-implementation-plan
        #       [@create-agents-symlinks-implementation-plan]

        lines = result.output.strip().split("\n")
        assert len(lines) == 3

        # Line 0: main (no indentation, no connector)
        assert lines[0].startswith("main")
        assert "[@root]" in lines[0]

        # Line 1: workstack-dev-cli-implementation (has connector, no leading spaces)
        assert "└─ workstack-dev-cli-implementation" in lines[1]
        assert "[@workstack-dev-cli-implementation]" in lines[1]

        # Line 2: create-agents-symlinks-implementation-plan (has connector
        # AND leading spaces for nesting). This is the critical check - it
        # should have "   └─" (3 spaces + connector), NOT just "└─" at the
        # beginning
        assert "   └─ create-agents-symlinks-implementation-plan" in lines[2]
        assert "[@create-agents-symlinks-implementation-plan]" in lines[2]


def test_tree_root_on_non_trunk_branch() -> None:
    """Test tree when root worktree is on a non-trunk branch.

    Scenario:
    - Root is on "cleanup" branch
    - "cleanup" has parent "main" in Graphite
    - "main" is trunk but has no worktree
    - Should show "cleanup" as root of tree (orphaned parent)

    This tests the fix for the bug where tree shows "No worktrees found"
    when the root worktree is on a non-main branch.
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        repo_root = env.cwd

        # Cache has cleanup as child of main, but only cleanup has a worktree
        branches = {
            "main": BranchMetadata.trunk("main", children=["cleanup"]),
            "cleanup": BranchMetadata.branch(
                "cleanup", parent="main", children=["feature-a", "feature-b"]
            ),
            "feature-a": BranchMetadata.branch("feature-a", parent="cleanup"),
            "feature-b": BranchMetadata.branch("feature-b", parent="cleanup"),
        }

        # Root worktree is on "cleanup", not "main"
        # "main" has NO worktree
        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="cleanup"),
                    WorktreeInfo(
                        path=env.workstacks_root / "feature-a",
                        branch="feature-a",
                    ),
                    WorktreeInfo(
                        path=env.workstacks_root / "feature-b",
                        branch="feature-b",
                    ),
                ]
            },
            current_branches={repo_root: "cleanup"},
        )

        graphite_ops = FakeGraphiteOps(branches=branches)

        ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=graphite_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["tree"], obj=ctx)

        assert result.exit_code == 0

        # Should show all three worktrees
        assert "cleanup" in result.output
        assert "feature-a" in result.output
        assert "feature-b" in result.output

        # "cleanup" should appear as root (orphaned from main)
        # "feature-a" and "feature-b" should be children of cleanup
        assert "[@root]" in result.output  # cleanup is the root worktree

        # Verify tree structure has connectors
        assert "└─" in result.output or "├─" in result.output

        # Should NOT show "No worktrees found"
        assert "No worktrees found" not in result.output
