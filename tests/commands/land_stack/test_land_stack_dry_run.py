"""Tests for land-stack --dry-run flag.

Tests verify that dry-run mode does NOT execute write operations like merge_pr,
but still performs read operations for validation.
"""

from pathlib import Path
from unittest.mock import Mock

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.abc import WorktreeInfo
from erk.core.git.fake import FakeGit
from erk.core.github.fake import FakeGitHub
from erk.core.graphite.fake import FakeGraphite
from tests.fakes.shell import FakeShell
from tests.test_utils.builders import BranchStackBuilder, PullRequestInfoBuilder
from tests.test_utils.env_helpers import erk_inmem_env


class TrackableFakeGitHub(FakeGitHub):
    """FakeGitHub with call tracking for dry-run tests.

    Extends FakeGitHub to track all write operation calls (merge_pr,
    update_pr_base_branch) to verify they are NOT called in dry-run mode.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.merge_pr_calls: list[tuple[int, bool]] = []
        self.update_pr_base_calls: list[tuple[int, str]] = []

    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
    ) -> None:
        """Record merge_pr call before delegating."""
        self.merge_pr_calls.append((pr_number, squash))
        super().merge_pr(repo_root, pr_number, squash=squash, verbose=verbose)

    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """Record update_pr_base_branch call before delegating."""
        self.update_pr_base_calls.append((pr_number, new_base))
        super().update_pr_base_branch(repo_root, pr_number, new_base)


def test_dry_run_does_not_execute_merge_operations() -> None:
    """Test that --dry-run flag prevents PR merge operations from executing.

    This is a CRITICAL test - it catches the bug where dry-run actually merges PRs.
    This test MUST FAIL before the fix is applied.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up a simple stack: main -> feat-1 -> feat-2
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

        # Configure Graphite metadata for stack
        graphite_ops = FakeGraphite(
            branches=BranchStackBuilder().add_linear_stack("feat-1", "feat-2").build(),
            stacks={
                "feat-2": ["main", "feat-1", "feat-2"],
            },
        )

        # Configure trackable GitHub ops with PRs
        github_ops = TrackableFakeGitHub(
            prs={
                "feat-1": PullRequestInfoBuilder(101, "feat-1").with_passing_checks().build(),
                "feat-2": PullRequestInfoBuilder(102, "feat-2").with_passing_checks().build(),
            },
            pr_bases={
                101: "main",
                102: "feat-1",
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

        # Act: Run land-stack with --dry-run flag and --force to skip confirmation
        result = runner.invoke(cli, ["land-stack", "--dry-run", "--force"], obj=test_ctx)

        # Assert: Command should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: merge_pr should NOT have been called (THIS IS THE BUG)
        assert len(github_ops.merge_pr_calls) == 0, (
            f"merge_pr was called {len(github_ops.merge_pr_calls)} times in dry-run mode! "
            f"Calls: {github_ops.merge_pr_calls}"
        )


def test_dry_run_does_not_execute_checkout_operations() -> None:
    """Test that --dry-run flag prevents git checkout operations from executing.

    This test verifies the fix for the critical bug where DryRunGit.checkout_branch()
    was incorrectly delegating to the wrapped implementation instead of being a no-op.
    This test MUST FAIL before the fix is applied and PASS after.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up a simple stack: main -> feat-1 -> feat-2
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

        # Track checkout_branch calls on the real git implementation
        checkout_spy = Mock()
        original_checkout = git_ops.checkout_branch

        def tracked_checkout(cwd: Path, branch: str) -> None:
            checkout_spy(branch)
            return original_checkout(cwd, branch)

        git_ops.checkout_branch = tracked_checkout

        # Configure Graphite metadata for stack
        graphite_ops = FakeGraphite(
            branches=BranchStackBuilder().add_linear_stack("feat-1", "feat-2").build(),
            stacks={
                "feat-2": ["main", "feat-1", "feat-2"],
            },
        )

        # Configure GitHub ops with PRs
        github_ops = TrackableFakeGitHub(
            prs={
                "feat-1": PullRequestInfoBuilder(101, "feat-1").with_passing_checks().build(),
                "feat-2": PullRequestInfoBuilder(102, "feat-2").with_passing_checks().build(),
            },
            pr_bases={
                101: "main",
                102: "feat-1",
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

        # Act: Run land-stack with --dry-run flag and --force to skip confirmation
        result = runner.invoke(cli, ["land-stack", "--dry-run", "--force"], obj=test_ctx)

        # Assert: Command should succeed
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: checkout_branch should NOT have been called
        # Note: In dry-run mode, DryRunGit wrapper prevents the call from reaching
        # the underlying FakeGit
        assert checkout_spy.call_count == 0, (
            f"checkout_branch was called {checkout_spy.call_count} times in dry-run mode! "
            f"Calls: {checkout_spy.call_args_list}"
        )


def test_dry_run_still_performs_read_operations() -> None:
    """Test that --dry-run still performs read operations for validation.

    Dry-run mode should:
    - Read PR statuses (to validate all branches have PRs)
    - Read PR mergeability (to check for conflicts)
    - Read PR base branches (for validation)

    But NOT execute write operations.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up stack with missing PR (will cause validation failure)
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

        graphite_ops = FakeGraphite(
            branches=BranchStackBuilder().add_linear_stack("feat-1", "feat-2").build(),
            stacks={
                "feat-2": ["main", "feat-1", "feat-2"],
            },
        )

        # Only feat-1 has a PR, feat-2 does not
        github_ops = TrackableFakeGitHub(
            prs={
                "feat-1": PullRequestInfoBuilder(101, "feat-1").with_passing_checks().build(),
            },
            pr_bases={101: "main"},
        )

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            dry_run=False,
        )

        # Act: Run with --dry-run
        result = runner.invoke(cli, ["land-stack", "--dry-run", "--force"], obj=test_ctx)

        # Assert: Should fail validation because feat-2 has no PR
        # This proves that read operations (get_pr_status) are still working
        assert result.exit_code != 0
        assert "feat-2" in result.output  # Should mention the problematic branch


def test_dry_run_shows_all_operations() -> None:
    """Test that dry-run shows all operations that would be performed.

    Verifies that dry-run output is comprehensive and shows:
    - PR merge commands
    - Sync commands
    - Submit commands for remaining branches
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up stack: main -> feat-1 -> feat-2
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

        graphite_ops = FakeGraphite(
            branches=BranchStackBuilder().add_linear_stack("feat-1", "feat-2").build(),
            stacks={
                "feat-2": ["main", "feat-1", "feat-2"],
            },
        )

        github_ops = TrackableFakeGitHub(
            prs={
                "feat-1": PullRequestInfoBuilder(101, "feat-1").with_passing_checks().build(),
                "feat-2": PullRequestInfoBuilder(102, "feat-2").with_passing_checks().build(),
            },
            pr_bases={
                101: "main",
                102: "feat-1",
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

        # Act: Run with --dry-run
        result = runner.invoke(cli, ["land-stack", "--dry-run", "--force"], obj=test_ctx)

        # Assert: Command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: Output shows all expected operations
        # Note: DryRunOps now prints styled output, execution layer skips output for dry-run
        output = result.output
        assert "gh pr merge 101" in output or "gh pr merge" in output, (
            "Should show PR merge operations"
        )
        assert "(dry run)" in output, "Should show dry run indicators"
        assert "gt sync" in output, "Should show sync operation"
        assert "gt submit" in output, "Should show submit operations for remaining branches"


def test_dry_run_does_not_delete_branches() -> None:
    """Test that dry-run does not delete branches.

    Verifies that dry-run mode does not perform destructive git operations like
    deleting branches. Note: Checkouts are allowed for validation purposes.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up stack
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

        github_ops = TrackableFakeGitHub(
            prs={
                "feat-1": PullRequestInfoBuilder(101, "feat-1").with_passing_checks().build(),
            },
            pr_bases={101: "main"},
        )

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            dry_run=False,
        )

        # Act: Run with --dry-run
        result = runner.invoke(cli, ["land-stack", "--dry-run", "--force"], obj=test_ctx)

        # Assert: Command succeeded
        assert result.exit_code == 0

        # Assert: No branches were deleted (DryRunGit prevents this)
        assert len(git_ops.deleted_branches) == 0, "No branches should be deleted in dry-run mode"


def test_dry_run_does_not_update_pr_bases() -> None:
    """Test that dry-run does not update PR base branches on GitHub.

    Phase 6 of land-stack updates PR base branches after sync. This should
    NOT happen in dry-run mode.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up 3-branch stack
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

        graphite_ops = FakeGraphite(
            branches=BranchStackBuilder().add_linear_stack("feat-1", "feat-2").build(),
            stacks={
                "feat-2": ["main", "feat-1", "feat-2"],
            },
        )

        github_ops = TrackableFakeGitHub(
            prs={
                "feat-1": PullRequestInfoBuilder(101, "feat-1").with_passing_checks().build(),
                "feat-2": PullRequestInfoBuilder(102, "feat-2").with_passing_checks().build(),
            },
            pr_bases={
                101: "main",
                102: "feat-1",
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

        # Act: Run with --dry-run
        result = runner.invoke(cli, ["land-stack", "--dry-run", "--force"], obj=test_ctx)

        # Assert: Command succeeded
        assert result.exit_code == 0

        # Assert: No PR base updates were made
        assert len(github_ops.update_pr_base_calls) == 0, (
            f"update_pr_base_branch should not be called in dry-run mode, "
            f"but was called {len(github_ops.update_pr_base_calls)} times"
        )
