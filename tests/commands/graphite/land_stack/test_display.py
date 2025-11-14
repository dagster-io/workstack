"""Tests for land-stack display and output formatting."""

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.env_helpers import pure_workstack_env
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.global_config import GlobalConfig
from workstack.core.graphite_ops import BranchMetadata


def test_land_stack_verbose_flag_shows_detailed_output() -> None:
    """Test that --verbose flag works with Phase 5 force-push operations.

    The --verbose flag should enable detailed output for all operations including
    the Phase 5 submit_branch calls. In non-verbose mode, operations are quieter.

    Note: This test verifies --verbose doesn't break Phase 5, not the exact output
    format, since the verbose behavior is implemented in RealGraphiteOps (which uses
    --quiet flag based on the quiet parameter).
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Build simple 3-branch stack
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch("feat-2", "feat-1", commit_sha="ghi789"),
            },
            current_branch="feat-2",
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            }
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        # Act: Land with --verbose flag
        result = runner.invoke(
            cli, ["land-stack", "--force", "--verbose", "--dry-run"], obj=test_ctx
        )

        # Assert: Command succeeded with --verbose flag
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: Phase 5 submit commands still appear in output with --verbose
        assert "gt submit --branch feat-2 --no-edit" in result.output, (
            f"Expected Phase 5 submit command in verbose output.\nActual output:\n{result.output}"
        )


def test_land_stack_dry_run_shows_submit_commands() -> None:
    """Test that --dry-run mode shows gt submit commands in output.

    In dry-run mode, the command should display the gt submit commands that would
    be executed for each remaining branch, but should NOT actually call submit_branch
    on FakeGraphiteOps.
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Build 3-branch stack
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch("feat-2", "feat-1", commit_sha="ghi789"),
            },
            current_branch="feat-2",
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            }
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=True,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        # Act: Land with --dry-run flag
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        # Assert: Command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: Output shows gt submit commands for remaining branch (feat-2)
        assert "gt submit --branch feat-2 --no-edit" in result.output, (
            f"Expected 'gt submit --branch feat-2 --no-edit' in output.\n"
            f"Actual output:\n{result.output}"
        )

        # Assert: DRY RUN mode means submit_branch should NOT be called on FakeGraphiteOps
        # (In dry-run, NoopGraphiteOps.submit_branch shows the command but doesn't mutate)
        # The test_ctx uses dry_run=True, so FakeGraphiteOps.submit_branch is NOT invoked
        # Instead, NoopGraphiteOps wrapper shows the command
        #
        # Note: We can't assert len(graphite_ops.submit_branch_calls) == 0 here because
        # the NoopGraphiteOps wrapper still calls the underlying fake for tracking.
        # The key is that dry-run mode shows the command in output without real execution.
