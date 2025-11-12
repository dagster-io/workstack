"""Tests for land-stack execution logic."""

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.env_helpers import pure_workstack_env
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.global_config import GlobalConfig
from workstack.core.graphite_ops import BranchMetadata


def test_land_stack_force_pushes_remaining_branches_after_sync() -> None:
    """Test that land-stack force-pushes remaining branches after each sync.

    Bug: After landing feat-1 and running gt sync -f, Graphite rebases remaining
    branches (feat-2, feat-3) locally, but they weren't pushed to GitHub. This left
    GitHub PRs showing stale commits with duplicated history.

    Fix: Phase 5 added to force-push all remaining branches after each sync operation,
    ensuring GitHub PRs reflect the rebased commits.

    This test verifies the fix by checking that submit_branch is called for each
    remaining branch after landing a PR.
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Build 4-branch stack: main → feat-1 → feat-2 → feat-3
        # Current: feat-2 (will land feat-1, leaving feat-2 and feat-3 remaining)
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch(
                    "feat-2", "feat-1", children=["feat-3"], commit_sha="ghi789"
                ),
                "feat-3": BranchMetadata.branch("feat-3", "feat-2", commit_sha="jkl012"),
            },
            current_branch="feat-2",
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
                "feat-3": ("OPEN", 300, "Feature 3"),
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

        # Act: Land feat-1 (leaving feat-2 and feat-3 as remaining branches)
        # Use --force to skip confirmation, --dry-run to see what would be executed
        result = runner.invoke(cli, ["land-stack", "--force", "--dry-run"], obj=test_ctx)

        # Assert: Command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: Phase 5 should show submit commands for remaining branches (feat-2, feat-3)
        # After landing feat-1, gt sync rebases feat-2 and feat-3
        # Phase 5 force-pushes both branches
        assert "gt submit --branch feat-2 --no-edit" in result.output, (
            f"Expected 'gt submit --branch feat-2 --no-edit' in output.\n"
            f"Actual output:\n{result.output}"
        )
        assert "gt submit --branch feat-3 --no-edit" in result.output, (
            f"Expected 'gt submit --branch feat-3 --no-edit' in output.\n"
            f"Actual output:\n{result.output}"
        )


def test_land_stack_force_pushes_after_each_pr_landed() -> None:
    """Test that land-stack force-pushes remaining branches after EACH PR is landed.

    When landing multiple PRs (feat-1, feat-2), each gt sync -f rebases the remaining
    branches. Phase 5 must run after EACH sync to keep GitHub PRs in sync.

    Expected submit_branch calls:
    - After landing feat-1: submit feat-2, feat-3, feat-4 (3 calls)
    - After landing feat-2: submit feat-3, feat-4 (2 calls)
    - Total: 5 submit_branch calls
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Build 5-branch stack: main → feat-1 → feat-2 → feat-3 → feat-4
        # Current: feat-3 (will land feat-1 and feat-2)
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch(
                    "feat-2", "feat-1", children=["feat-3"], commit_sha="ghi789"
                ),
                "feat-3": BranchMetadata.branch(
                    "feat-3", "feat-2", children=["feat-4"], commit_sha="jkl012"
                ),
                "feat-4": BranchMetadata.branch("feat-4", "feat-3", commit_sha="mno345"),
            },
            current_branch="feat-3",
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
                "feat-3": ("OPEN", 300, "Feature 3"),
                "feat-4": ("OPEN", 400, "Feature 4"),
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

        # Act: Land feat-1, feat-2, and feat-3 (leaving feat-4)
        # Current branch is feat-3, so land-stack lands from bottom to current
        result = runner.invoke(cli, ["land-stack", "--force", "--dry-run"], obj=test_ctx)

        # Assert: Command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: Phase 5 runs after each PR is landed, showing submit commands
        # After feat-1: submit feat-2, feat-3, feat-4 (3 submits)
        # After feat-2: submit feat-3, feat-4 (2 submits)
        # After feat-3: submit feat-4 (1 submit)
        # Verify all remaining branches are submitted after each PR
        assert "gt submit --branch feat-2 --no-edit" in result.output, (
            f"Expected feat-2 submit command in output.\nActual output:\n{result.output}"
        )
        assert "gt submit --branch feat-3 --no-edit" in result.output, (
            f"Expected feat-3 submit command in output.\nActual output:\n{result.output}"
        )
        assert "gt submit --branch feat-4 --no-edit" in result.output, (
            f"Expected feat-4 submit command in output.\nActual output:\n{result.output}"
        )

        # Count occurrences to verify submit happens after each PR land
        # feat-2 should appear once (after landing feat-1)
        # feat-3 should appear twice (after landing feat-1 and feat-2)
        # feat-4 should appear three times (after landing feat-1, feat-2, and feat-3)
        output_lines = result.output
        feat2_count = output_lines.count("gt submit --branch feat-2 --no-edit")
        feat3_count = output_lines.count("gt submit --branch feat-3 --no-edit")
        feat4_count = output_lines.count("gt submit --branch feat-4 --no-edit")

        assert feat2_count == 1, f"Expected feat-2 submitted 1 time, got {feat2_count}"
        assert feat3_count == 2, f"Expected feat-3 submitted 2 times, got {feat3_count}"
        assert feat4_count == 3, f"Expected feat-4 submitted 3 times, got {feat4_count}"


def test_land_stack_no_submit_when_landing_top_branch() -> None:
    """Test that no submit_branch calls are made when landing the top/leaf branch.

    When landing the top branch of a stack, there are no remaining branches upstack.
    Phase 5 should detect this and skip submit_branch calls entirely.
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Build 3-branch stack: main → feat-1 → feat-2 → feat-3
        # Current: feat-3 (top/leaf branch)
        # Landing all 3 branches, final branch has no remaining upstack
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch(
                    "feat-2", "feat-1", children=["feat-3"], commit_sha="ghi789"
                ),
                "feat-3": BranchMetadata.branch("feat-3", "feat-2", commit_sha="jkl012"),
            },
            current_branch="feat-3",
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
                "feat-3": ("OPEN", 300, "Feature 3"),
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

        # Act: Land entire stack (feat-1, feat-2, feat-3)
        result = runner.invoke(cli, ["land-stack", "--force", "--dry-run"], obj=test_ctx)

        # Assert: Command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: Phase 5 should show submit commands after feat-1 and feat-2, but NOT after feat-3
        # After feat-1: submit feat-2, feat-3
        # After feat-2: submit feat-3
        # After feat-3: no remaining branches (no submit commands)

        # Count occurrences to verify
        # feat-2 should appear once (after landing feat-1 only)
        # feat-3 should appear twice (after landing feat-1 and feat-2)
        output = result.output
        feat2_count = output.count("gt submit --branch feat-2 --no-edit")
        feat3_count = output.count("gt submit --branch feat-3 --no-edit")

        assert feat2_count == 1, (
            f"Expected feat-2 submitted 1 time (after feat-1), got {feat2_count}\nOutput:\n{output}"
        )
        assert feat3_count == 2, (
            f"Expected feat-3 submitted 2 times (after feat-1 and feat-2), got {feat3_count}\n"
            f"Output:\n{output}"
        )

        # Verify no "Phase 5" operations after the final PR (feat-3)
        # This is implicitly tested by the counts above - if there were operations after
        # feat-3, we'd see additional submit commands


def test_land_stack_switches_to_root_when_run_from_linked_worktree() -> None:
    """Test that land-stack switches to root worktree before cleanup.

    Scenario: User is in a linked worktree that will be destroyed during land-stack.
    Without the fix, the user's shell ends up in a destroyed directory.

    Bug: land-stack runs cleanup operations (including workstack sync -f) which
    destroys worktrees. If the current directory is one of those worktrees, the
    shell is left in a deleted directory.

    Fix: Before cleanup, check if Path.cwd() != repo.root and call os.chdir(repo.root).

    Note: In pure mode, we test that the command handles linked worktree contexts
    without filesystem side effects. The actual os.chdir() behavior is tested in
    integration tests with real filesystem.
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Create linked worktree for feat-1 (chdir is ignored in pure mode)
        linked_wt = env.create_linked_worktree(name="feat-1-work", branch="feat-1", chdir=False)

        # Build ops for simple stack: main → feat-1
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feat-1"],
                    commit_sha="abc123",
                    is_trunk=True,
                ),
                "feat-1": BranchMetadata(
                    name="feat-1",
                    parent="main",
                    children=[],
                    commit_sha="def456",
                    is_trunk=False,
                ),
            },
            current_branch="feat-1",
            current_worktree=linked_wt,
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Add feature 1"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
            cwd=linked_wt,
        )

        # Run land-stack with --dry-run to avoid subprocess failures
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        # Verify the command completed successfully when run from linked worktree
        # The actual os.chdir() behavior is tested in integration tests
        assert result.exit_code == 0
        assert "Landing 1 PR" in result.output
        assert "feat-1" in result.output


def test_land_stack_merge_command_excludes_auto_flag() -> None:
    """Test that land-stack merge commands do NOT include --auto flag.

    Regression test for GitHub auto-merge issue:
    - The --auto flag requires branch protection rules to be configured
    - Without protection rules, GitHub returns "Pull request is in clean status" error
    - land-stack uses synchronous sequential landing, so auto-merge provides no value

    This test ensures the --auto flag remains removed from merge commands.
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Build simple stack with one PR
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            current_branch="feat-1",
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
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

        # Run in dry-run mode to see the commands that would be executed
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify merge command appears in output
        assert "gh pr merge 100 --squash" in result.output, (
            f"Expected merge command not found in output:\n{result.output}"
        )

        # Verify --auto flag is NOT present in merge command
        assert "--auto" not in result.output, (
            f"The --auto flag should NOT appear in merge commands. "
            f"This flag requires branch protection rules and provides no value "
            f"for synchronous sequential landing. Actual output:\n{result.output}"
        )
