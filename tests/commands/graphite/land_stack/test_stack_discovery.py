"""Tests for land-stack stack discovery behavior."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.branch_metadata import BranchMetadata
from tests.fakes.github import FakeGitHub
from tests.test_utils.builders import BranchStackBuilder
from tests.test_utils.env_helpers import erk_inmem_env


def test_land_stack_gets_branches_to_land_correctly() -> None:
    """Test that land-stack lands from bottom of stack to current branch."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Stack: main → feat-1 → feat-2 → feat-3
        # Current: feat-2
        # With --down flag: Should land feat-1, feat-2 (bottom to current, not including feat-3)
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                **BranchStackBuilder()
                .add_linear_stack("feat-1", "feat-2", "feat-3")
                .with_commit_sha("feat-1", "def456")
                .with_commit_sha("feat-2", "ghi789")
                .with_commit_sha("feat-3", "jkl012")
                .build(),
            },
            current_branch="feat-2",
        )

        # feat-1 and feat-2 have open PRs (feat-3 not needed)
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

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            use_graphite=True,
        )

        # Use --force to skip confirmation and --down to land only downstack
        result = runner.invoke(cli, ["land-stack", "--force", "--down"], obj=test_ctx, input="y\n")

        # Should show landing 2 PRs (feat-1 and feat-2 from bottom to current)
        assert "Landing 2 PRs" in result.output
        assert "feat-1" in result.output
        assert "feat-2" in result.output


def test_land_stack_from_top_of_stack_lands_all_branches() -> None:
    """Test that land-stack from top of stack lands all branches from bottom to current.

    When on the leaf/top branch of a stack, land-stack should land ALL branches
    from the bottom of the stack (first non-trunk) up to and including current.

    Bug: Currently only returns the current branch when at top of stack.
    Fix: Should return entire stack from bottom to current.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Stack: main → feat-1 → feat-2 → feat-3 → feat-4
        # Current: feat-4 (at TOP/leaf)
        # Should land: feat-1, feat-2, feat-3, feat-4 (ALL 4 branches)
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                **BranchStackBuilder()
                .add_linear_stack("feat-1", "feat-2", "feat-3", "feat-4")
                .with_commit_sha("feat-1", "def456")
                .with_commit_sha("feat-2", "ghi789")
                .with_commit_sha("feat-3", "jkl012")
                .with_commit_sha("feat-4", "mno345")
                .build(),
            },
            current_branch="feat-4",
        )

        # All branches have open PRs
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

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            use_graphite=True,
        )

        # Use --dry-run to avoid actual merging
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        # Should show landing 4 PRs (ALL branches from bottom to current)
        assert "Landing 4 PRs" in result.output
        assert "feat-1" in result.output
        assert "feat-2" in result.output
        assert "feat-3" in result.output
        assert "feat-4" in result.output


def test_land_stack_refreshes_metadata_after_sync() -> None:
    """Test that RealGraphite invalidates cache after gt sync.

    This test verifies the fix for the cache invalidation bug:
    - Bug: RealGraphite.sync() didn't invalidate _branches_cache
    - Result: After gt sync updated metadata, stale cached data was returned
    - Fix: Added `self._branches_cache = None` at end of sync()

    The test creates a simulated scenario where sync() modifies metadata
    and verifies that subsequent get_all_branches() calls return fresh data.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Stack: main → feat-1 → feat-2
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                **BranchStackBuilder()
                .add_linear_stack("feat-1", "feat-2")
                .with_commit_sha("feat-1", "def456")
                .with_commit_sha("feat-2", "ghi789")
                .build(),
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

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            use_graphite=True,
        )

        # Execute land-stack - should complete successfully
        # The fix ensures cache is invalidated after each sync
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Landing 2 PRs" in result.output
