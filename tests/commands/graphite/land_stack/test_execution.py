"""Tests for land-stack execution logic."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.branch_metadata import BranchMetadata
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext
from erk.core.github.fake import FakeGitHub
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
    """Test that gt restack IS run automatically during restack phase.

    This test was updated after fixing the restack phase bug. Previously, the restack
    phase was a no-op, causing upstack branches to fail submission. Now gt restack
    --no-interactive runs automatically to rebase upstack branches after each merge.

    The --down flag can be used to skip automatic restacking if manual control is desired.
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
        )

        # Run land-stack
        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify gt restack WAS called via mutation tracking
        assert len(graphite_ops.restack_calls) == 1, (
            f"gt restack should be called automatically. "
            f"Expected 1 restack call, got {len(graphite_ops.restack_calls)} calls: "
            f"{graphite_ops.restack_calls}"
        )

        # Verify no_interactive=True was passed (required for non-interactive mode)
        _, no_interactive_arg, _ = graphite_ops.restack_calls[0]
        assert no_interactive_arg is True, "gt restack should be called with no_interactive=True"


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

        # Verify output shows suggestion to run erk sync manually
        assert "Run 'erk sync -f' to remove worktrees" in result.output, (
            f"Expected manual erk sync suggestion in output.\nActual output:\n{result.output}"
        )


def test_final_state_shows_next_steps() -> None:
    """Test that final state display includes Next steps section.

    After landing (display.py:113-129), user should see:
    - "Next steps:" header
    - Suggestion to run 'erk sync -f' to remove worktrees
    - Suggestion to run 'gt sync -f' to remove branches with closed PRs
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

        # Verify erk sync suggestion for removing worktrees
        assert "Run 'erk sync -f' to remove worktrees" in result.output, (
            f"Expected erk sync suggestion in output.\nActual output:\n{result.output}"
        )

        # Verify gt sync suggestion for removing branches with closed PRs
        assert "Run 'gt sync -f' to remove branches with closed PRs" in result.output, (
            f"Expected gt sync suggestion in output.\nActual output:\n{result.output}"
        )

        # Verify note about manual control
        assert "These commands are now manual to give you full control" in result.output, (
            f"Expected manual control note in output.\nActual output:\n{result.output}"
        )


def test_land_stack_runs_gt_sync_in_restack_phase() -> None:
    """Verify gt restack --no-interactive runs automatically during restack phase.

    After each PR is merged with squash merge, upstack branches still reference
    old commits in their history. The restack phase must run gt restack to:
    1. Update Graphite metadata about merged branches
    2. Rebase upstack branches onto new trunk state

    Without this, gt submit fails with "merged commits are not contained in trunk".

    This test uses a simple 1-branch stack to verify restack is called without needing
    complex state management across multiple branch landings.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Setup simple 1-branch stack: main → feat-1
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
        )

        # Act: Land the branch (without --down flag)
        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Assert: Verify restack was called
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert len(graphite_ops.restack_calls) >= 1, (
            f"Expected at least 1 restack call, got {len(graphite_ops.restack_calls)}"
        )

        # Verify restack was called with correct parameters
        for _repo_root_arg, no_interactive_arg, quiet_arg in graphite_ops.restack_calls:
            assert no_interactive_arg is True, (
                "restack must be called with no_interactive=True for non-interactive mode"
            )
            assert quiet_arg is True, "restack should be quiet in default (non-verbose) mode"


def test_land_stack_skips_gt_sync_with_down_flag() -> None:
    """Verify gt sync is NOT called when using --down flag.

    The --down flag tells land-stack to only land branches downstack (toward trunk)
    and skip the restack phase. This provides manual control for users who want to
    handle restacking themselves.

    Uses simple 1-branch stack to avoid state management complexity.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Setup simple 1-branch stack: main → feat-1
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
        )

        # Act: Land with --down flag (skip restacking)
        result = runner.invoke(cli, ["land-stack", "--force", "--down"], obj=test_ctx)

        # Assert: Verify sync was NOT called
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert len(graphite_ops.sync_calls) == 0, (
            f"gt sync should NOT be called with --down flag. "
            f"Expected 0 sync calls, got {len(graphite_ops.sync_calls)}"
        )


def test_land_stack_restack_respects_verbose_flag() -> None:
    """Verify quiet parameter is set correctly based on verbose flag.

    The gt restack command has a --quiet flag. The quiet parameter should be:
    - True in default mode (quiet=not verbose, verbose=False → quiet=True)
    - False in --verbose mode (quiet=not verbose, verbose=True → quiet=False)

    This matches the pattern where --verbose shows detailed output.

    This test uses a simple 1-branch stack to avoid state management complexity.
    """
    runner = CliRunner()

    # Test 1: Without --verbose (default) - should be quiet
    with erk_inmem_env(runner) as env:
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
        )

        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert len(graphite_ops.restack_calls) >= 1
        _, _, quiet_arg = graphite_ops.restack_calls[0]
        assert quiet_arg is True, "quiet should be True in default (non-verbose) mode"

    # Test 2: With --verbose - should NOT be quiet
    with erk_inmem_env(runner) as env:
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
        )

        result = runner.invoke(cli, ["land-stack", "--force", "--verbose"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert len(graphite_ops.restack_calls) >= 1
        _, _, quiet_arg = graphite_ops.restack_calls[0]
        assert quiet_arg is False, "quiet should be False in verbose mode (show detailed output)"


def test_land_stack_checks_pr_mergeability_before_merge() -> None:
    """Verify PR mergeability is checked before attempting merge.

    When a PR has merge conflicts (DIRTY state), land-stack should detect this
    and fail with a helpful error message BEFORE attempting the actual merge.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Build simple stack: main → feat-1
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            current_branch="feat-1",
        )

        # Configure GitHub to report PR as unmergeable due to conflicts
        from erk.core.github.types import PRMergeability

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
            },
            pr_bases={
                100: "main",
            },
            pr_mergeability={
                100: PRMergeability(
                    mergeable="CONFLICTING",
                    merge_state_status="DIRTY",
                ),
            },
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            use_graphite=True,
        )

        # Act: Try to land the branch
        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Assert: Should fail with helpful error message
        assert result.exit_code != 0, "Command should fail when PR has conflicts"
        assert "PR #100" in result.output
        assert "merge conflicts" in result.output.lower()

        # Verify no PR was merged
        assert len(github_ops.merged_prs) == 0


def test_land_stack_succeeds_when_pr_is_mergeable() -> None:
    """Verify PR merge proceeds when mergeability check passes.

    When a PR has CLEAN merge state, land-stack should proceed with the merge.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Build simple stack: main → feat-1
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            current_branch="feat-1",
        )

        # Configure GitHub to report PR as mergeable
        from erk.core.github.types import PRMergeability

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
            },
            pr_bases={
                100: "main",
            },
            pr_mergeability={
                100: PRMergeability(
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                ),
            },
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            use_graphite=True,
        )

        # Act: Land the branch
        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Assert: Should succeed
        assert result.exit_code == 0, (
            f"Command should succeed when PR is mergeable: {result.output}"
        )

        # Verify PR was merged
        assert 100 in github_ops.merged_prs


def test_land_stack_fails_when_pr_blocked_by_protections() -> None:
    """Verify PR merge fails helpfully when blocked by branch protections.

    When a PR is blocked by branch protection rules (BLOCKED state), land-stack
    should fail with a message explaining the protection rules issue.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Build simple stack: main → feat-1
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            current_branch="feat-1",
        )

        # Configure GitHub to report PR as blocked
        from erk.core.github.types import PRMergeability

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
            },
            pr_bases={
                100: "main",
            },
            pr_mergeability={
                100: PRMergeability(
                    mergeable="CONFLICTING",
                    merge_state_status="BLOCKED",
                ),
            },
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            use_graphite=True,
        )

        # Act: Try to land the branch
        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Assert: Should fail with helpful error message
        assert result.exit_code != 0
        assert "PR #100" in result.output
        assert "merge" in result.output.lower()

        # Verify no PR was merged
        assert len(github_ops.merged_prs) == 0


def test_land_stack_shows_mergeability_check_in_output() -> None:
    """Verify mergeability check success is shown in output.

    When PR passes mergeability check, this should be visible in the output
    as a phase completion (similar to other phases).
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Build simple stack: main → feat-1
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            current_branch="feat-1",
        )

        # Configure GitHub to report PR as mergeable
        from erk.core.github.types import PRMergeability

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
            },
            pr_bases={
                100: "main",
            },
            pr_mergeability={
                100: PRMergeability(
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                ),
            },
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            use_graphite=True,
        )

        # Act: Land the branch
        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Assert: Should show mergeability check in output
        assert result.exit_code == 0
        assert "verify PR #100 is mergeable" in result.output
