"""Tests for land-stack cleanup and navigation logic."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.context import ErkContext
from erk.core.global_config import GlobalConfig
from erk.core.graphite_ops import BranchMetadata
from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.env_helpers import erk_inmem_env


def test_land_stack_cleanup_respects_master_trunk() -> None:
    """Test that land-stack cleanup checks out 'master' when repository uses master as trunk.

    Bug: The cleanup logic hardcoded 'main' as the final checkout branch, causing
    incorrect behavior for repositories using 'master' as their trunk branch.

    Fix: Cleanup function now accepts trunk_branch parameter and uses it for
    final checkout, respecting the detected trunk branch from the repository.

    This test verifies the fix by:
    1. Setting up a repository with 'master' as trunk (not 'main')
    2. Running land-stack to land a merged PR
    3. Asserting the final checkout is to 'master' (not hardcoded 'main')
    4. Asserting command output shows 'git checkout master'
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Build 2-branch stack: master → feat-1
        # Current: feat-1 (will land feat-1)
        # Note: Using "master" instead of "main" to expose the hardcoded bug
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "master": BranchMetadata.trunk("master", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "master", commit_sha="def456"),
            },
            current_branch="feat-1",
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
            },
            pr_bases={
                100: "main",
            },
        )

        global_config_ops = GlobalConfig(
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        test_ctx = ErkContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=True,  # Use dry-run to see commands
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        # Act: Land feat-1 (should checkout master at end, not main)
        result = runner.invoke(cli, ["land-stack", "--force", "--dry-run"], obj=test_ctx)

        # Assert: Command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: Cleanup should checkout 'master', not 'main'
        assert "git checkout master" in result.output, (
            f"Expected 'git checkout master' in cleanup.\n"
            f"Bug: cleanup is hardcoded to 'main' instead of using detected trunk.\n"
            f"Actual output:\n{result.output}"
        )

        # Assert: Should NOT contain 'git checkout main' (the bug we're fixing)
        assert "git checkout main" not in result.output, (
            f"Found 'git checkout main' in output - cleanup should use 'master' for this repo.\n"
            f"Actual output:\n{result.output}"
        )
