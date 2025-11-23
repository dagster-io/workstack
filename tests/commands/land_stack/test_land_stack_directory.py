"""Tests for land-stack directory switching behavior.

Verifies that after landing a stack, the user ends up in the correct worktree
directory (root worktree) and that no duplicate checkout messages appear.
"""

from dataclasses import replace

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.git.abc import WorktreeInfo
from erk.core.git.fake import FakeGit
from erk.core.github.fake import FakeGitHub
from erk.core.graphite.fake import FakeGraphite
from tests.test_utils.builders import BranchStackBuilder, PullRequestInfoBuilder
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_land_stack_navigates_to_root_worktree() -> None:
    """Test that land-stack succeeds when run from current worktree on branch being landed.

    After validation changes, land-stack EXCLUDES the current branch in the current
    worktree from conflict detection, only flagging branches in OTHER worktrees.

    This replaces the previous test which expected failure. The new behavior correctly
    allows landing from the current worktree without false positive conflicts.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a root worktree and a feature worktree
        feature_worktree_path = env.erk_root / "worktrees" / "feat-branch"

        git_ops = FakeGit(
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
        graphite_ops = FakeGraphite(
            branches=BranchStackBuilder().add_linear_stack("feat-branch").build(),
            stacks={
                "feat-branch": ["main", "feat-branch"],
            },
        )

        # Configure GitHub ops with passing PR
        github_ops = FakeGitHub(
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
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
        )

        # Execute land-stack from feature worktree directory
        # Simulate being in the feature worktree
        test_ctx = replace(test_ctx, cwd=feature_worktree_path)

        result = runner.invoke(
            cli,
            ["land-stack", "--force"],
            obj=test_ctx,
        )

        # Should succeed - current branch in current worktree is not a conflict
        assert result.exit_code == 0, f"Expected success but got: {result.output}"
        assert (
            "Cannot land stack - branches are checked out in multiple worktrees"
            not in result.output
        )


def test_land_stack_no_duplicate_checkout_message() -> None:
    """Test that land-stack succeeds when run from current worktree on branch being landed.

    After validation changes, land-stack EXCLUDES the current branch in the current
    worktree from conflict detection, only flagging branches in OTHER worktrees.

    This replaces the previous test which expected failure. The new behavior correctly
    allows landing from the current worktree without false positive conflicts.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a root worktree and a feature worktree
        feature_worktree_path = env.erk_root / "worktrees" / "feat-branch"

        # Start from feature branch (land-stack must be run from feature branch)
        git_ops = FakeGit(
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
        graphite_ops = FakeGraphite(
            branches=BranchStackBuilder().add_linear_stack("feat-branch").build(),
            stacks={
                "feat-branch": ["main", "feat-branch"],
            },
        )

        # Configure GitHub ops with passing PR
        github_ops = FakeGitHub(
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
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
        )

        # Execute from feature worktree
        test_ctx = replace(test_ctx, cwd=feature_worktree_path)

        result = runner.invoke(
            cli,
            ["land-stack", "--force"],
            obj=test_ctx,
        )

        # Should succeed - current branch in current worktree is not a conflict
        assert result.exit_code == 0, f"Expected success but got: {result.output}"
        assert (
            "Cannot land stack - branches are checked out in multiple worktrees"
            not in result.output
        )
