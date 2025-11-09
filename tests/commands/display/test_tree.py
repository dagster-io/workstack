"""Tests for workstack tree command.

This file tests CLI-specific behavior: command execution, error handling, and output formatting.
Pure business logic (graph filtering, tree building, rendering) is tested in
tests/unit/hierarchy/test_branch_graph.py.
"""

import tempfile
from pathlib import Path

from click.testing import CliRunner

from tests.fakes.context import create_test_context
from tests.fakes.gitops import FakeGitOps, WorktreeInfo
from tests.fakes.global_config_ops import FakeGlobalConfigOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.test_utils.repo_setup import simulated_workstack_env
from workstack.cli.cli import cli
from workstack.cli.tree import (
    _get_worktree_mapping,
    _load_graphite_branch_graph,
)
from workstack.core.graphite_ops import BranchMetadata

# ===========================
# Integration Tests (Functions with Filesystem)
# ===========================


def test_get_worktree_mapping(monkeypatch) -> None:
    """Test worktree mapping creation from git worktrees."""
    repo_root = Path("/repo")
    workstacks_dir = Path("/repo/work")

    # Mock Path.cwd() to return repo_root so it detects as current worktree
    monkeypatch.setattr("pathlib.Path.cwd", lambda: repo_root)

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

    ctx = create_test_context(git_ops=git_ops)

    mapping = _get_worktree_mapping(ctx, repo_root)

    assert mapping.branch_to_worktree == {
        "main": "root",
        "feature-a": "feature-a",
        "feature-b": "feature-b",
    }
    assert "root" in mapping.worktree_to_path
    assert mapping.current_worktree == "root"


def test_get_worktree_mapping_skips_detached_head(monkeypatch) -> None:
    """Test that worktrees with detached HEAD are skipped."""
    repo_root = Path("/repo")

    # Mock Path.cwd() to return repo_root
    monkeypatch.setattr("pathlib.Path.cwd", lambda: repo_root)

    git_ops = FakeGitOps(
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main"),
                WorktreeInfo(path=Path("/repo/work/detached"), branch=None),
            ]
        },
    )

    ctx = create_test_context(git_ops=git_ops)

    mapping = _get_worktree_mapping(ctx, repo_root)

    # Should only have main, not the detached HEAD worktree
    assert mapping.branch_to_worktree == {"main": "root"}


def test_get_worktree_mapping_detects_current_from_subdirectory(monkeypatch) -> None:
    """Test that current worktree is detected when cwd is a subdirectory."""
    repo_root = Path("/repo")
    feature_worktree = Path("/repo/work/feature-a")
    subdirectory = feature_worktree / "src" / "module"

    # Mock Path.cwd() to return subdirectory within feature-a worktree
    monkeypatch.setattr("pathlib.Path.cwd", lambda: subdirectory)

    git_ops = FakeGitOps(
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main"),
                WorktreeInfo(path=feature_worktree, branch="feature-a"),
            ]
        },
    )

    ctx = create_test_context(git_ops=git_ops)

    mapping = _get_worktree_mapping(ctx, repo_root)

    # Should detect feature-a as current even though cwd is in subdirectory
    assert mapping.current_worktree == "feature-a"


def test_get_worktree_mapping_handles_user_outside_all_worktrees(monkeypatch) -> None:
    """Test behavior when user is not in any worktree."""
    repo_root = Path("/repo")
    outside_path = Path("/tmp/somewhere-else")

    # Mock Path.cwd() to return path outside all worktrees
    monkeypatch.setattr("pathlib.Path.cwd", lambda: outside_path)

    git_ops = FakeGitOps(
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main"),
                WorktreeInfo(path=Path("/repo/work/feature-a"), branch="feature-a"),
            ]
        },
    )

    ctx = create_test_context(git_ops=git_ops)

    mapping = _get_worktree_mapping(ctx, repo_root)

    # Should have no current worktree
    assert mapping.current_worktree is None


def test_load_graphite_branch_graph() -> None:
    """Test loading branch graph from Graphite cache."""
    repo_root = Path("/repo")

    # Configure FakeGraphiteOps with branch metadata
    branches = {
        "main": BranchMetadata.main(
            children=["feature-a", "feature-b"],
        ),
        "feature-a": BranchMetadata.branch(
            "feature-a",
            parent="main",
            children=[],
        ),
        "feature-b": BranchMetadata.branch(
            "feature-b",
            parent="main",
            children=["feature-b-2"],
        ),
        "feature-b-2": BranchMetadata.branch(
            "feature-b-2",
            parent="feature-b",
            children=[],
        ),
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
    repo_root = Path("/repo")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_git_dir = Path(tmpdir) / ".git"
        tmp_git_dir.mkdir()
        # No cache file created

        git_ops = FakeGitOps(git_common_dirs={repo_root: tmp_git_dir})
        ctx = create_test_context(git_ops=git_ops)

        graph = _load_graphite_branch_graph(ctx, repo_root)

        assert graph is None


# ===========================
# CLI Command Tests
# ===========================


def test_tree_command_displays_hierarchy() -> None:
    """Test that tree command shows worktree hierarchy."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create feature-a worktree
        env.create_linked_worktree("feature-a", "feature-a", chdir=False)

        # Build ops from branches
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(children=["feature-a"], sha="abc123"),
                "feature-a": BranchMetadata.branch("feature-a", sha="def456"),
            },
            current_branch="main",
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
        )

        ctx = create_test_context(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
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
    with simulated_workstack_env(runner) as env:
        # Only create worktree for feature-a (not feature-b)
        env.create_linked_worktree("feature-a", "feature-a", chdir=False)

        # Build ops with 3 branches, but only 2 have worktrees
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(children=["feature-a", "feature-b"], sha="abc123"),
                "feature-a": BranchMetadata.branch("feature-a", sha="def456"),
                "feature-b": BranchMetadata.branch("feature-b", sha="ghi789"),
            },
            current_branch="main",
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
        )

        ctx = create_test_context(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
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
    with simulated_workstack_env(runner) as env:
        # Build git_ops only - NO graphite_ops to simulate missing cache
        worktrees_list = [WorktreeInfo(path=env.root_worktree, branch="main", is_root=True)]

        git_ops = FakeGitOps(
            worktrees={env.root_worktree: worktrees_list},
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.root_worktree / ".git"},
            default_branches={env.root_worktree: "main"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
        )

        # Don't provide graphite_ops - this simulates missing cache
        ctx = create_test_context(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
        )

        result = runner.invoke(cli, ["tree"], obj=ctx)

        assert result.exit_code == 1
        assert "Graphite cache not found" in result.output
        assert "tree' command requires Graphite" in result.output


def test_tree_command_shows_nested_hierarchy() -> None:
    """Test tree command with 3-level nested hierarchy."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create worktrees for all branches
        env.create_linked_worktree("parent", "parent", chdir=False)
        env.create_linked_worktree("child", "child", chdir=False)

        # Build ops from branches
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(children=["parent"], sha="abc123"),
                "parent": BranchMetadata.branch("parent", children=["child"], sha="def456"),
                "child": BranchMetadata.branch("child", parent="parent", sha="ghi789"),
            },
            current_branch="main",
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root, use_graphite=True
        )

        ctx = create_test_context(
            git_ops=git_ops, graphite_ops=graphite_ops, global_config_ops=global_config_ops
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
    with simulated_workstack_env(runner) as env:
        # Create worktrees for nested stack
        env.create_linked_worktree(
            "workstack-dev-cli-implementation", "workstack-dev-cli-implementation", chdir=False
        )
        env.create_linked_worktree(
            "create-agents-symlinks-implementation-plan",
            "create-agents-symlinks-implementation-plan",
            chdir=False,
        )

        # Build ops from branches
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(
                    children=["workstack-dev-cli-implementation"], sha="abc123"
                ),
                "workstack-dev-cli-implementation": BranchMetadata.branch(
                    "workstack-dev-cli-implementation",
                    children=["create-agents-symlinks-implementation-plan"],
                    sha="def456",
                ),
                "create-agents-symlinks-implementation-plan": BranchMetadata.branch(
                    "create-agents-symlinks-implementation-plan",
                    parent="workstack-dev-cli-implementation",
                    sha="ghi789",
                ),
            },
            current_branch="main",
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root, use_graphite=True
        )

        ctx = create_test_context(
            git_ops=git_ops, graphite_ops=graphite_ops, global_config_ops=global_config_ops
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
    with simulated_workstack_env(runner) as env:
        # Create worktrees for cleanup's children
        env.create_linked_worktree("feature-a", "feature-a", chdir=False)
        env.create_linked_worktree("feature-b", "feature-b", chdir=False)

        # Build branches - main exists in graph but won't have a worktree
        branches = {
            "main": BranchMetadata.main(children=["cleanup"], sha="abc123"),
            "cleanup": BranchMetadata.branch(
                "cleanup", children=["feature-a", "feature-b"], sha="def456"
            ),
            "feature-a": BranchMetadata.branch("feature-a", parent="cleanup", sha="ghi789"),
            "feature-b": BranchMetadata.branch("feature-b", parent="cleanup", sha="jkl012"),
        }

        # Manually construct worktrees with root on "cleanup" instead of "main"
        worktrees_list = [
            WorktreeInfo(path=env.root_worktree, branch="cleanup", is_root=True),
            WorktreeInfo(
                path=env.workstacks_root / "repo" / "feature-a", branch="feature-a", is_root=False
            ),
            WorktreeInfo(
                path=env.workstacks_root / "repo" / "feature-b", branch="feature-b", is_root=False
            ),
        ]

        git_ops = FakeGitOps(
            worktrees={env.root_worktree: worktrees_list},
            current_branches={
                env.root_worktree: "cleanup",
                env.workstacks_root / "repo" / "feature-a": "feature-a",
                env.workstacks_root / "repo" / "feature-b": "feature-b",
            },
            git_common_dirs={wt.path: env.root_worktree / ".git" for wt in worktrees_list},
            default_branches={env.root_worktree: "main"},
        )

        # Build stacks from branches
        stacks = {
            "cleanup": ["cleanup"],
            "feature-a": ["cleanup", "feature-a"],
            "feature-b": ["cleanup", "feature-b"],
        }

        graphite_ops = FakeGraphiteOps(branches=branches, stacks=stacks)

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root, use_graphite=True
        )

        ctx = create_test_context(
            git_ops=git_ops, graphite_ops=graphite_ops, global_config_ops=global_config_ops
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
