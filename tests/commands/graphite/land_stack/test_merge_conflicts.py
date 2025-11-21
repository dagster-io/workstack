"""Tests for land-stack merge conflict detection."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.branch_metadata import BranchMetadata
from erk.core.github.types import PRMergeability
from tests.fakes.github import FakeGitHub
from tests.test_utils.builders import BranchStackBuilder
from tests.test_utils.env_helpers import erk_inmem_env


def test_land_stack_fails_when_first_pr_has_conflict() -> None:
    """Test that land-stack fails when first PR has merge conflict."""
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

        # feat-1 has CONFLICTING status
        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            },
            pr_mergeability={
                100: PRMergeability(mergeable="CONFLICTING", merge_state_status="DIRTY"),
                200: PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN"),
            },
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Should fail before user confirmation
        assert result.exit_code == 1
        assert "Cannot land stack - PRs have merge conflicts" in result.output
        assert "PR #100 (feat-1): has conflicts with main" in result.output
        assert "gt stack rebase" in result.output


def test_land_stack_fails_when_middle_pr_has_conflict() -> None:
    """Test that land-stack fails when middle PR has merge conflict."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Stack: main → feat-1 → feat-2 → feat-3
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
            current_branch="feat-3",
        )

        # feat-2 (middle PR) has CONFLICTING status
        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
                "feat-3": ("OPEN", 300, "Feature 3"),
            },
            pr_mergeability={
                100: PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN"),
                200: PRMergeability(mergeable="CONFLICTING", merge_state_status="DIRTY"),
                300: PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN"),
            },
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Should fail before user confirmation
        assert result.exit_code == 1
        assert "Cannot land stack - PRs have merge conflicts" in result.output
        assert "PR #200 (feat-2): has conflicts with main" in result.output


def test_land_stack_fails_when_last_pr_has_conflict() -> None:
    """Test that land-stack fails when last PR has merge conflict."""
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

        # feat-2 (last PR) has CONFLICTING status
        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            },
            pr_mergeability={
                100: PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN"),
                200: PRMergeability(mergeable="CONFLICTING", merge_state_status="DIRTY"),
            },
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Should fail before user confirmation
        assert result.exit_code == 1
        assert "Cannot land stack - PRs have merge conflicts" in result.output
        assert "PR #200 (feat-2): has conflicts with main" in result.output


def test_land_stack_succeeds_with_unknown_mergeability() -> None:
    """Test that land-stack proceeds with warning when PR mergeability is UNKNOWN."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Simple stack: main → feat-1
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            current_branch="feat-1",
        )

        # feat-1 has UNKNOWN status (GitHub hasn't computed it yet)
        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
            },
            pr_mergeability={
                100: PRMergeability(mergeable="UNKNOWN", merge_state_status="UNKNOWN"),
            },
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Should show warning but not fail
        assert "Warning: PR #100 mergeability unknown" in result.output
        # Should proceed to show landing plan (exit code depends on dry-run success)


def test_land_stack_succeeds_when_all_prs_mergeable() -> None:
    """Test that land-stack succeeds when all PRs are MERGEABLE."""
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

        # All PRs are MERGEABLE
        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            },
            pr_mergeability={
                100: PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN"),
                200: PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN"),
            },
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Should pass validation and show landing plan
        assert "Cannot land stack - PRs have merge conflicts" not in result.output
        assert "Landing 2 PRs" in result.output
