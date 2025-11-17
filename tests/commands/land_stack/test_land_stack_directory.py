"""Tests for land-stack directory switching behavior.

Verifies that after landing a stack, the user ends up in the correct worktree
directory (root worktree) and that no duplicate checkout messages appear.
"""

from dataclasses import replace

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.branch_metadata import BranchMetadata
from erk.core.gitops import WorktreeInfo
from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.test_utils.builders import PullRequestInfoBuilder
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_land_stack_navigates_to_root_worktree() -> None:
    """Test that land-stack fails when run from a worktree with a branch being landed.

    After validation changes, land-stack requires all branches in the stack to NOT be
    checked out in worktrees when landing. The user must consolidate first or run from
    root worktree.

    This replaces the previous test which verified directory navigation when landing
    from within a worktree. That scenario is no longer supported.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a root worktree and a feature worktree
        feature_worktree_path = env.erk_root / "worktrees" / "feat-branch"

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir, feature_worktree_path: env.git_dir},
            default_branches={env.cwd: "main", feature_worktree_path: "main"},
            current_branches={env.cwd: "main", feature_worktree_path: "feat-branch"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_worktree_path, branch="feat-branch", is_root=False),
                ],
            },
        )

        # Configure Graphite metadata for simple stack
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-branch"]),
                "feat-branch": BranchMetadata.branch("feat-branch", parent="main"),
            },
            stacks={
                "feat-branch": ["main", "feat-branch"],
            },
        )

        # Configure GitHub ops with passing PR
        github_ops = FakeGitHubOps(
            prs={
                "feat-branch": (
                    PullRequestInfoBuilder(101, "feat-branch").with_passing_checks().build()
                ),
            },
            pr_bases={
                101: "main",
            },
        )

        test_ctx = env.build_context(
            use_graphite=True,
            git_ops=git_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
        )

        # Execute land-stack from feature worktree directory
        # Simulate being in the feature worktree
        test_ctx = replace(test_ctx, cwd=feature_worktree_path)

        result = runner.invoke(
            cli,
            ["land-stack", "--force"],
            obj=test_ctx,
        )

        # Should fail with worktree conflict error
        assert result.exit_code == 1, f"Expected failure but got: {result.output}"
        assert "Cannot land stack - branches are checked out in multiple worktrees" in result.output
        assert "feat-branch" in result.output
        assert "erk consolidate" in result.output


def test_land_stack_no_duplicate_checkout_message() -> None:
    """Test that land-stack fails when run from a worktree with a branch being landed.

    After validation changes, land-stack requires all branches in the stack to NOT be
    checked out in worktrees when landing. The user must consolidate first or run from
    root worktree.

    This replaces the previous test which verified duplicate checkout message prevention
    when landing from within a worktree. That scenario is no longer supported.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a root worktree and a feature worktree
        feature_worktree_path = env.erk_root / "worktrees" / "feat-branch"

        # Start from feature branch (land-stack must be run from feature branch)
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir, feature_worktree_path: env.git_dir},
            default_branches={env.cwd: "main", feature_worktree_path: "main"},
            current_branches={env.cwd: "main", feature_worktree_path: "feat-branch"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_worktree_path, branch="feat-branch", is_root=False),
                ],
            },
        )

        # Configure Graphite metadata for simple stack
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-branch"]),
                "feat-branch": BranchMetadata.branch("feat-branch", parent="main"),
            },
            stacks={
                "feat-branch": ["main", "feat-branch"],
            },
        )

        # Configure GitHub ops with passing PR
        github_ops = FakeGitHubOps(
            prs={
                "feat-branch": (
                    PullRequestInfoBuilder(101, "feat-branch").with_passing_checks().build()
                ),
            },
            pr_bases={
                101: "main",
            },
        )

        test_ctx = env.build_context(
            use_graphite=True,
            git_ops=git_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
        )

        # Execute from feature worktree
        test_ctx = replace(test_ctx, cwd=feature_worktree_path)

        result = runner.invoke(
            cli,
            ["land-stack", "--force"],
            obj=test_ctx,
        )

        # Should fail with worktree conflict error
        assert result.exit_code == 1, f"Expected failure but got: {result.output}"
        assert "Cannot land stack - branches are checked out in multiple worktrees" in result.output
        assert "feat-branch" in result.output
        assert "erk consolidate" in result.output
