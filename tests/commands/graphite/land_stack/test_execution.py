"""Tests for land-stack execution logic."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext
from erk.core.graphite import BranchMetadata
from tests.fakes.github import FakeGitHub
from tests.fakes.shell import FakeShell
from tests.test_utils.env_helpers import erk_inmem_env


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
    with erk_inmem_env(runner) as env:
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

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
                "feat-3": ("OPEN", 300, "Feature 3"),
            },
            pr_bases={
                100: "main",
                200: "main",
                300: "main",
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
    with erk_inmem_env(runner) as env:
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

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
                "feat-3": ("OPEN", 300, "Feature 3"),
                "feat-4": ("OPEN", 400, "Feature 4"),
            },
            pr_bases={
                100: "main",
                200: "main",
                300: "main",
                400: "main",
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
    with erk_inmem_env(runner) as env:
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

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
                "feat-3": ("OPEN", 300, "Feature 3"),
            },
            pr_bases={
                100: "main",
                200: "main",
                300: "main",
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
    """Test that land-stack succeeds when run from current worktree on branch being landed.

    Scenario: User is in a linked worktree where the current branch is being landed.
    The validation should EXCLUDE the current branch in the current worktree from conflicts.

    After fix: Validation correctly excludes the current branch in the current worktree,
    only flagging branches checked out in OTHER worktrees as conflicts.

    Note: This replaces the previous behavior where validation would incorrectly flag
    the current branch as a worktree conflict even though it's naturally checked out
    in the current worktree.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
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
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Add feature 1"),
            },
            pr_bases={
                100: "main",
            },
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            dry_run=False,
            cwd=linked_wt,
        )

        # Run land-stack with --dry-run to avoid subprocess failures
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        # Should succeed - current branch in current worktree is not a conflict
        assert result.exit_code == 0
        assert (
            "Cannot land stack - branches are checked out in multiple worktrees"
            not in result.output
        )


def test_land_stack_merge_command_excludes_auto_flag() -> None:
    """Test that land-stack merge commands do NOT include --auto flag.

    Regression test for GitHub auto-merge issue:
    - The --auto flag requires branch protection rules to be configured
    - Without protection rules, GitHub returns "Pull request is in clean status" error
    - land-stack uses synchronous sequential landing, so auto-merge provides no value

    This test ensures the --auto flag remains removed from merge commands.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Build simple stack with one PR
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            current_branch="feat-1",
        )

        github_ops = FakeGitHub(
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
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
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


def test_land_stack_does_not_run_gt_sync() -> None:
    """Test that gt sync -f is NOT run automatically during landing.

    After behavior change (execution.py:203-205), gt sync -f is manual, not automatic.
    This test verifies that graphite_ops.sync() is never called during the landing sequence.

    Rationale: Automatic gt sync -f was destructive and ran without user control.
    Now users must run it manually after landing.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Build simple 2-branch stack: main → feat-1
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            current_branch="feat-1",
        )

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
            },
            pr_bases={
                100: "main",
            },
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            use_graphite=True,
            dry_run=True,
        )

        # Run land-stack
        result = runner.invoke(cli, ["land-stack", "--force", "--dry-run"], obj=test_ctx)

        # Should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify gt sync was NOT called via mutation tracking
        assert len(graphite_ops.sync_calls) == 0, (
            f"gt sync should NOT be called automatically. "
            f"Expected 0 sync calls, got {len(graphite_ops.sync_calls)} calls: "
            f"{graphite_ops.sync_calls}"
        )

        # Verify gt sync command doesn't appear in execution phases
        # Note: It WILL appear in "Next steps" as a manual suggestion, which is correct
        # We're verifying it's not executed automatically
        assert "Executing: gt sync" not in result.output, (
            f"gt sync should NOT be executed automatically.\nActual output:\n{result.output}"
        )
        assert "(dry run) gt sync" not in result.output, (
            f"gt sync should NOT be shown in dry-run execution.\nActual output:\n{result.output}"
        )


def test_land_stack_does_not_run_erk_sync() -> None:
    """Test that gt sync -f is NOT run automatically after landing.

    After behavior change (cleanup.py:143), gt sync -f is manual, not automatic.
    This test verifies that shell_ops.run_erk_sync() is never called, and worktrees
    remain after landing completes.

    Rationale: Automatic gt sync -f removed worktrees without user control.
    Now users must run it manually after landing.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Build simple 2-branch stack: main → feat-1
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            current_branch="feat-1",
        )

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
            },
            pr_bases={
                100: "main",
            },
        )

        shell_ops = FakeShell()

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=shell_ops,
            use_graphite=True,
            dry_run=True,
        )

        # Run land-stack
        result = runner.invoke(cli, ["land-stack", "--force", "--dry-run"], obj=test_ctx)

        # Should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify gt sync was NOT called via mutation tracking
        assert len(shell_ops.sync_calls) == 0, (
            f"gt sync should NOT be called automatically. "
            f"Expected 0 sync calls, got {len(shell_ops.sync_calls)} calls: {shell_ops.sync_calls}"
        )

        # Verify output shows suggestion to run gt sync manually
        assert "Run 'gt sync -f' to remove worktrees" in result.output, (
            f"Expected manual gt sync suggestion in output.\nActual output:\n{result.output}"
        )


def test_final_state_shows_next_steps() -> None:
    """Test that final state display includes Next steps section.

    After landing (display.py:113-129), user should see:
    - "Next steps:" header
    - Suggestion to run 'gt sync -f' to remove worktrees
    - Suggestion to run 'gt sync -f' to rebase remaining branches
    - Note about manual control

    This ensures users are informed about follow-up actions after landing.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Build simple 2-branch stack: main → feat-1
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            current_branch="feat-1",
        )

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
            },
            pr_bases={
                100: "main",
            },
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            use_graphite=True,
            dry_run=True,
        )

        # Run land-stack
        result = runner.invoke(cli, ["land-stack", "--force", "--dry-run"], obj=test_ctx)

        # Should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify "Next steps" section appears
        assert "Next steps:" in result.output, (
            f"Expected 'Next steps:' header in output.\nActual output:\n{result.output}"
        )

        # Verify gt sync suggestion for removing worktrees
        assert "Run 'gt sync -f' to remove worktrees" in result.output, (
            f"Expected gt sync suggestion in output.\nActual output:\n{result.output}"
        )

        # Verify gt sync suggestion
        assert "Run 'gt sync -f' to rebase remaining stack branches" in result.output, (
            f"Expected gt sync suggestion in output.\nActual output:\n{result.output}"
        )

        # Verify note about manual control
        assert "These commands are now manual to give you full control" in result.output, (
            f"Expected manual control note in output.\nActual output:\n{result.output}"
        )
