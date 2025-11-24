"""Tests for land-stack PR operations and GitHub interactions."""

from click.testing import CliRunner
from erk_shared.git.abc import WorktreeInfo

from erk.cli.cli import cli
from erk.core.branch_metadata import BranchMetadata
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext
from erk.core.git.fake import FakeGit
from erk.core.github.fake import FakeGitHub
from erk.core.graphite.fake import FakeGraphite
from tests.fakes.shell import FakeShell
from tests.test_utils.env_helpers import erk_inmem_env


def test_land_stack_skips_base_update_when_already_correct() -> None:
    """Test that land-stack skips PR base update when already correct.

    When GitHub PR base already matches expected parent, we should not
    make unnecessary API calls to update it.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Build two-PR stack
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

        # Configure FakeGitHub with correct bases (matching Graphite parents)
        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            },
            pr_bases={
                100: "main",  # Matches Graphite parent
                200: "feat-1",  # Matches Graphite parent
            },
        )

        global_config_ops = GlobalConfig(
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            dry_run=True,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify that no PR base update messages appear (base already correct)
        assert "Updating PR #100 base:" not in result.output, (
            f"No base update message should appear when base is already correct\n"
            f"Actual output: {result.output}"
        )
        assert "Updating PR #200 base:" not in result.output, (
            f"No base update message should appear when base is already correct\n"
            f"Actual output: {result.output}"
        )


def test_land_stack_updates_pr_bases_after_force_push() -> None:
    """Test that land-stack updates PR bases on GitHub AFTER force-pushing rebased commits.

    Bug scenario:
    - Stack: main → feat-1 → feat-2
    - When landing feat-1, gt sync rebases feat-2 onto main
    - PR #200's base on GitHub is still "feat-1" (stale)
    - Without fix: Base update happens before force-push, GitHub rejects it
    - With fix: Base update happens AFTER force-push in Phase 6

    This test verifies the fix by checking that gh pr edit commands appear
    in the correct order in dry-run output.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Build initial Graphite/Git state
        # Running from feat-1, which will land only feat-1
        # After sync, feat-2's parent will be updated to "main"
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ],
            },
            current_branches={env.cwd: "feat-1"},
            existing_paths={env.cwd, env.git_dir},
        )

        # Graphite metadata showing POST-sync state:
        # - feat-2's parent is "main" (what it will be after landing feat-1 and syncing)
        # - feat-1 still has feat-2 as a child (for finding upstack branches)
        # - Stack includes full history for proper navigation
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-2"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch("feat-2", "main", commit_sha="ghi789"),
            },
            stacks={
                "feat-1": ["main", "feat-1"],
                "feat-2": ["main", "feat-1", "feat-2"],
            },
        )

        # Configure GitHub with stale base for PR #200
        # After landing feat-1, Graphite updates feat-2's parent to "main"
        # but GitHub still shows base as "feat-1" (this is the bug)
        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            },
            pr_bases={
                100: "main",  # Correct
                200: "feat-1",  # Stale - will be updated to "main" after force-push
            },
        )

        global_config_ops = GlobalConfig(
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            dry_run=True,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        # Run land-stack with --dry-run to see command execution order
        result = runner.invoke(cli, ["land-stack", "--force", "--dry-run"], obj=test_ctx)

        # Assert: Command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: Phase 6 should show PR base update command AFTER force-push
        # The key fix: gh pr edit happens after gt submit (force-push)
        assert "gh pr edit 200 --base main" in result.output, (
            f"Expected 'gh pr edit 200 --base main' in output.\n"
            f"This command should appear in Phase 6, AFTER force-push.\n"
            f"Actual output:\n{result.output}"
        )


def test_land_stack_dry_run_shows_trunk_sync_commands() -> None:
    """Test that land-stack --dry-run shows trunk sync commands in output.

    Verifies that dry-run mode displays the git commands for trunk syncing
    so users can see what would happen.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Build 2-branch stack
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

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            },
            pr_bases={
                100: "main",
                200: "main",
            },
        )

        global_config_ops = GlobalConfig(
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            dry_run=True,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        # Act: Run with --dry-run to see commands
        result = runner.invoke(cli, ["land-stack", "--force", "--dry-run"], obj=test_ctx)

        # Assert: Command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: Output contains trunk sync commands (after each merge)
        assert "git fetch origin main" in result.output, (
            f"Expected 'git fetch origin main' in dry-run output.\nActual output:\n{result.output}"
        )
        assert "git checkout main" in result.output, (
            f"Expected 'git checkout main' in dry-run output.\nActual output:\n{result.output}"
        )
        assert "git pull --ff-only origin main" in result.output, (
            f"Expected 'git pull --ff-only origin main' in dry-run output.\n"
            f"Actual output:\n{result.output}"
        )

        # Assert: Checkout back to branch after sync
        # After landing feat-1, should checkout back to feat-1
        assert "git checkout feat-1" in result.output, (
            f"Expected 'git checkout feat-1' to return to branch after trunk sync.\n"
            f"Actual output:\n{result.output}"
        )
