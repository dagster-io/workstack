"""Tests for land-stack race condition with stale PR bases.

This test reproduces the bug where child PRs get merged into deleted parent
branches, creating orphaned merge commits that never reach main.

The race condition occurs when:
1. Parent PR merges and deletes its branch (e.g., feat-1)
2. Child PR's base on GitHub still points to deleted branch
3. Child PR merges before base is updated
4. Result: Orphaned merge commit that exists on GitHub but not in any branch

The fix adds Phase 2.5 that verifies and updates PR bases BEFORE merging.
"""

from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.abc import WorktreeInfo

from erk.cli.cli import cli
from erk.core.branch_metadata import BranchMetadata
from erk.core.git.fake import FakeGit
from erk.core.github.fake import FakeGitHub
from erk.core.graphite.fake import FakeGraphite
from tests.fakes.shell import FakeShell
from tests.test_utils.builders import BranchStackBuilder, PullRequestInfoBuilder
from tests.test_utils.env_helpers import erk_inmem_env


class TrackingFakeGitHub(FakeGitHub):
    """FakeGitHub that tracks get_pr_base_branch calls.

    Used to verify that PR base verification happens before merge.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.get_pr_base_calls: list[int] = []

    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str | None:
        """Track get_pr_base_branch calls for test assertions."""
        self.get_pr_base_calls.append(pr_number)
        return super().get_pr_base_branch(repo_root, pr_number)


def test_land_stack_detects_and_updates_stale_pr_base() -> None:
    """Test that land-stack detects stale PR base and updates before merge.

    This test reproduces the bug from PR #577 where:
    - Parent PR (#575, feat-1) merged and deleted its branch
    - Child PR (#577, feat-2) base still pointed to deleted feat-1
    - Child PR merged into deleted branch, creating orphaned commit 8735d8e6

    Expected behavior after fix:
    - Phase 2.5 checks PR base on GitHub before merge
    - Detects stale base (feat-1) doesn't match expected parent (main)
    - Updates PR base to main BEFORE attempting merge
    - No orphaned commits created

    This test MUST FAIL before the fix is applied.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up stack: main -> feat-1 -> feat-2
        # Simulate after feat-1 has already been landed:
        # - Local git parent of feat-2 is main (after previous iteration's restack)
        # - But GitHub PR #102 base is still "feat-1" (stale)
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feat-2"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ],
            },
        )

        # Configure Graphite metadata
        # After landing feat-1, the stack should look like: main -> feat-2
        graphite_ops = FakeGraphite(
            branches=BranchStackBuilder().add_linear_stack("feat-2").build(),
            stacks={
                "feat-2": ["main", "feat-2"],
            },
        )

        # Configure GitHub ops with STALE PR base
        # PR #102 (feat-2) base is "feat-1" but should be "main"
        github_ops = TrackingFakeGitHub(
            prs={
                "feat-2": PullRequestInfoBuilder(102, "feat-2").with_passing_checks().build(),
            },
            pr_bases={
                102: "feat-1",  # STALE - should be "main" after feat-1 landed
            },
        )

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            dry_run=False,
        )

        # Act: Land feat-2 (should detect stale base and update)
        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Assert: Command should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: PR base should have been checked (Phase 2.5)
        assert 102 in github_ops.get_pr_base_calls, (
            "get_pr_base_branch should be called for PR #102 in Phase 2.5"
        )

        # Assert: PR base should have been updated from "feat-1" to "main"
        assert (102, "main") in github_ops.updated_pr_bases, (
            f"PR #102 base should be updated from 'feat-1' to 'main' before merge. "
            f"Updated bases: {github_ops.updated_pr_bases}"
        )

        # Assert: PR merge should happen AFTER base update
        # This prevents orphaned commits
        assert 102 in github_ops.merged_prs, "PR #102 should be merged"

        # Verify ordering: get_pr_base -> update_pr_base -> merge_pr
        # This ensures Phase 2.5 runs before Phase 3
        get_base_index = len(github_ops.get_pr_base_calls) - 1  # Last check before merge
        update_base_found = False
        merge_found = False

        # Check that update happened after get_pr_base_branch call
        if github_ops.updated_pr_bases:
            update_base_found = True

        # Check that merge happened after update
        if github_ops.merged_prs and 102 in github_ops.merged_prs:
            merge_found = True

        assert get_base_index >= 0, "get_pr_base_branch should be called"
        assert update_base_found, "update_pr_base_branch should be called"
        assert merge_found, "merge_pr should be called"


def test_land_stack_skips_update_when_pr_base_already_correct() -> None:
    """Test that land-stack skips PR base update when base is already correct.

    When PR base on GitHub already matches the expected parent (trunk),
    Phase 2.5 should:
    - Check the PR base (get_pr_base_branch)
    - Find it matches expected parent
    - Skip update (no call to update_pr_base_branch)
    - Proceed with merge
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up stack with correct PR base
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feat-1"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ],
            },
        )

        graphite_ops = FakeGraphite(
            branches=BranchStackBuilder().add_linear_stack("feat-1").build(),
            stacks={
                "feat-1": ["main", "feat-1"],
            },
        )

        # PR base is CORRECT - already points to main
        github_ops = TrackingFakeGitHub(
            prs={
                "feat-1": PullRequestInfoBuilder(101, "feat-1").with_passing_checks().build(),
            },
            pr_bases={
                101: "main",  # CORRECT - matches parent
            },
        )

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            dry_run=False,
        )

        # Act: Land feat-1
        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Assert: Command should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: PR base should have been checked
        assert 101 in github_ops.get_pr_base_calls, (
            "get_pr_base_branch should be called for PR #101"
        )

        # Assert: PR base should NOT have been updated (already correct)
        assert (101, "main") not in github_ops.updated_pr_bases, (
            f"PR #101 base should NOT be updated when already correct. "
            f"Updated bases: {github_ops.updated_pr_bases}"
        )

        # Assert: PR should still be merged
        assert 101 in github_ops.merged_prs, "PR #101 should be merged"


def test_land_stack_with_multiple_branches_updates_all_stale_bases() -> None:
    """Test that land-stack handles stale bases correctly for multi-branch stacks.

    This test simulates landing a 3-branch stack where each PR's base becomes
    stale after the previous branch lands:
    - Initial stack: main -> feat-1 -> feat-2 -> feat-3
    - After landing feat-1: PR #102 base is stale (feat-1 deleted)
    - After landing feat-2: PR #103 base is stale (feat-2 deleted)

    Phase 2.5 should detect and fix each stale base before merging.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up 3-branch stack: main -> feat-1 -> feat-2 -> feat-3
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feat-3"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ],
            },
        )

        # Configure Graphite metadata
        # Simulate after feat-1 and feat-2 have landed: main -> feat-3
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"]),
                "feat-1": BranchMetadata.branch("feat-1", parent="main", children=["feat-2"]),
                "feat-2": BranchMetadata.branch("feat-2", parent="main", children=["feat-3"]),
                "feat-3": BranchMetadata.branch("feat-3", parent="main"),
            },
            stacks={
                "feat-3": ["main", "feat-1", "feat-2", "feat-3"],
            },
        )

        # Configure GitHub ops with PRs
        # All PR bases start correct, but we'll simulate them becoming stale
        # as each parent branch lands and is deleted
        github_ops = TrackingFakeGitHub(
            prs={
                "feat-1": PullRequestInfoBuilder(101, "feat-1").with_passing_checks().build(),
                "feat-2": PullRequestInfoBuilder(102, "feat-2").with_passing_checks().build(),
                "feat-3": PullRequestInfoBuilder(103, "feat-3").with_passing_checks().build(),
            },
            pr_bases={
                101: "main",  # CORRECT - feat-1 base is main
                102: "feat-1",  # STALE - feat-2 base should be main after feat-1 lands
                103: "feat-2",  # STALE - feat-3 base should be main after feat-2 lands
            },
        )

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            dry_run=False,
        )

        # Act: Land entire stack
        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Assert: Command should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: All PRs should have their bases checked
        assert 101 in github_ops.get_pr_base_calls, "PR #101 base should be checked"
        assert 102 in github_ops.get_pr_base_calls, "PR #102 base should be checked"
        assert 103 in github_ops.get_pr_base_calls, "PR #103 base should be checked"

        # Assert: PR #101 base should NOT be updated (already correct)
        pr_101_updates = [(pr, base) for pr, base in github_ops.updated_pr_bases if pr == 101]
        assert len(pr_101_updates) == 0, (
            f"PR #101 base should NOT be updated (already main). Updates: {pr_101_updates}"
        )

        # Assert: PR #102 base should be updated from feat-1 to main
        assert (102, "main") in github_ops.updated_pr_bases, (
            f"PR #102 base should be updated from 'feat-1' to 'main'. "
            f"Updated bases: {github_ops.updated_pr_bases}"
        )

        # Assert: PR #103 base should be updated from feat-2 to main
        assert (103, "main") in github_ops.updated_pr_bases, (
            f"PR #103 base should be updated from 'feat-2' to 'main'. "
            f"Updated bases: {github_ops.updated_pr_bases}"
        )

        # Assert: All PRs should be merged
        assert 101 in github_ops.merged_prs, "PR #101 should be merged"
        assert 102 in github_ops.merged_prs, "PR #102 should be merged"
        assert 103 in github_ops.merged_prs, "PR #103 should be merged"

        # Assert: No orphaned commits (all PRs merged successfully)
        assert len(github_ops.merged_prs) == 3, (
            f"All 3 PRs should be merged. Merged: {github_ops.merged_prs}"
        )
