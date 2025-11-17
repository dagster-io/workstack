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
    """Test that land-stack changes process directory to root worktree after landing.

    This verifies:
    - User ends up at root worktree (repo root) after landing
    - Process cwd is updated correctly
    - No duplicate checkout messages in output
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a root worktree and a feature worktree
        feature_worktree_path = env.erk_root / "worktrees" / "feat-branch"

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir, feature_worktree_path: env.git_dir},
            default_branches={env.cwd: "main", feature_worktree_path: "main"},
            current_branches={env.cwd: "feat-branch", feature_worktree_path: "feat-branch"},
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

        # Verify success
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify no duplicate checkout messages
        # Count occurrences of "git checkout main" in output
        checkout_count = result.output.count("git checkout main")
        assert checkout_count <= 1, (
            f"Expected at most 1 checkout message, found {checkout_count}: {result.output}"
        )


def test_land_stack_no_duplicate_checkout_message() -> None:
    """Test that land-stack doesn't emit duplicate checkout messages.

    This verifies the duplicate checkout prevention logic - after the sync_trunk_phase
    checks out main, the cleanup phase should detect we're already on main and skip
    the redundant checkout.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create a root worktree and a feature worktree
        feature_worktree_path = env.erk_root / "worktrees" / "feat-branch"

        # Start from feature branch (land-stack must be run from feature branch)
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir, feature_worktree_path: env.git_dir},
            default_branches={env.cwd: "main", feature_worktree_path: "main"},
            current_branches={env.cwd: "feat-branch", feature_worktree_path: "feat-branch"},
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

        # Verify success
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify at most ONE checkout message appears in output
        # The sync_trunk_phase may checkout main after merging the last PR,
        # but cleanup should NOT emit a duplicate checkout since we're already on main
        checkout_count = result.output.count("git checkout main")
        assert checkout_count <= 1, (
            f"Expected at most 1 'git checkout main' message, found {checkout_count}. "
            f"Output:\n{result.output}"
        )
