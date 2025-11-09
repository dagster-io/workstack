"""Unit tests for trunk branch detection logic.

These tests verify the business logic of `_is_trunk_branch` function, which determines
whether a branch should be treated as a trunk (main/master/develop) based on Graphite
cache metadata.

Business logic rules:
1. Branch with validationResult == "TRUNK" → True
2. Branch with no parent (parentBranchName == None) → True
3. Branch with a parent → False
4. Branch not in cache → False (default behavior)
"""

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.global_config_ops import FakeGlobalConfigOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.repo_setup import simulated_workstack_env
from workstack.cli.commands.list import _is_trunk_branch
from workstack.core.context import WorkstackContext
from workstack.core.graphite_ops import BranchMetadata


def test_branch_with_trunk_validation_result() -> None:
    """Branch with validationResult == "TRUNK" is identified as trunk."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build ops with main as trunk and feature-1 as child
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(children=["feature-1"], sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", parent="main", sha="def456"),
            },
            current_branch="main",
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
        )
        ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        assert _is_trunk_branch(ctx, env.root_worktree, "main") is True


def test_branch_with_no_parent_is_trunk() -> None:
    """Branch with parentBranchName == None but no TRUNK marker is still trunk."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build ops with orphan as trunk (no parent) and feature-1 as child
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "orphan": BranchMetadata.main(children=["feature-1"], sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", parent="orphan", sha="def456"),
            },
            current_branch="orphan",
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
        )
        ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        assert _is_trunk_branch(ctx, env.root_worktree, "orphan") is True


def test_branch_with_parent_is_not_trunk() -> None:
    """Branch with parentBranchName is not a trunk."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build ops with main as trunk and feature-1 as child
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(children=["feature-1"], sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", parent="main", sha="def456"),
            },
            current_branch="main",
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
        )
        ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        assert _is_trunk_branch(ctx, env.root_worktree, "feature-1") is False


def test_branch_not_in_cache_is_not_trunk() -> None:
    """Branch not present in graphite cache is not a trunk."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build ops with only main in cache
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(children=[], sha="abc123"),
            },
            current_branch="main",
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
        )
        ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        # Query for branch not in cache
        assert _is_trunk_branch(ctx, env.root_worktree, "unknown-branch") is False


def test_graphite_disabled_returns_false() -> None:
    """When Graphite is disabled, trunk detection returns False."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # When Graphite is disabled, configure FakeGraphiteOps to return empty
        # (simulating no Graphite cache available)
        git_ops, _unused_graphite_ops = env.build_ops_from_branches(
            {},  # Empty branches - no Graphite data
            current_branch="main",
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root,
            use_graphite=False,  # Graphite disabled
        )

        # Use empty FakeGraphiteOps (no branches configured)
        from tests.fakes.graphite_ops import FakeGraphiteOps

        ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=FakeGraphiteOps(),  # Empty ops
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        # Without Graphite, should return False (no way to detect trunk)
        assert _is_trunk_branch(ctx, env.root_worktree, "main") is False
