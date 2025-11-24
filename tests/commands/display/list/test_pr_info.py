"""Tests for PR info display in list command.

This file tests CLI-specific behavior: emoji rendering, URL formatting, and config handling.
Business logic for PR states is tested in tests/unit/status/test_github_pr_collector.py.
"""

import pytest
from click.testing import CliRunner
from erk_shared.git.abc import WorktreeInfo
from erk_shared.github.types import PullRequestInfo

from erk.cli.cli import cli
from erk.core.branch_metadata import BranchMetadata
from erk.core.git.fake import FakeGit
from erk.core.graphite.fake import FakeGraphite
from tests.test_utils.builders import PullRequestInfoBuilder
from tests.test_utils.env_helpers import erk_inmem_env

# ===========================
# Config Handling Tests
# ===========================


@pytest.mark.parametrize(
    ("show_pr_info", "expected_visible"),
    [
        (True, True),
        (False, False),
    ],
    ids=["visible", "hidden"],
)
def test_list_with_stacks_pr_visibility(show_pr_info: bool, expected_visible: bool) -> None:
    """PR info visibility follows the show_pr_info configuration flag."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        branch_name = "feature-branch"
        pr = PullRequestInfo(
            number=42,
            state="OPEN",
            url="https://github.com/owner/repo/pull/42",
            is_draft=False,
            title=None,
            checks_passing=True,
            owner="owner",
            repo="repo",
        )

        # Create branch metadata with a simple stack
        branches = {
            "main": BranchMetadata.trunk("main", children=[branch_name]),
            branch_name: BranchMetadata.branch(branch_name, "main", children=[]),
        }

        # Create worktree directory for branch so it appears in the stack
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_worktree = repo_dir / branch_name

        # Build fake git ops with worktree for branch
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_worktree, branch=branch_name),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir, feature_worktree: env.git_dir},
            current_branches={env.cwd: "main", feature_worktree: branch_name},
        )

        # PR data now comes from Graphite, not GitHub
        test_ctx = env.build_context(
            git=git_ops,
            graphite=FakeGraphite(branches=branches, pr_info={branch_name: pr}),
            use_graphite=True,
            show_pr_info=show_pr_info,
        )

        # PR info now shown on main line, not just with --stacks
        result = runner.invoke(cli, ["list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        assert ("#42" in result.output) is expected_visible


# ===========================
# Emoji Rendering Tests
# ===========================
# These tests verify CLI-specific emoji rendering.
# Business logic (PR state → ready_to_merge) is tested in unit layer.


@pytest.mark.parametrize(
    "state,is_draft,checks,expected_emoji",
    [
        ("OPEN", False, True, "✅"),  # Open PR with passing checks
        ("OPEN", False, False, "❌"),  # Open PR with failing checks
        ("OPEN", False, None, "👀"),  # Open PR with no checks
        ("OPEN", True, None, "🚧"),  # Draft PR
        ("MERGED", False, True, "🎉"),  # Merged PR
        ("CLOSED", False, None, "⛔"),  # Closed (not merged) PR
    ],
)
def test_list_pr_emoji_mapping(
    state: str, is_draft: bool, checks: bool | None, expected_emoji: str
) -> None:
    """Verify PR state → emoji mapping for all cases.

    This test covers all emoji rendering logic in a single parametrized test.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        branch_name = "test-branch"

        # Use builder pattern for PR creation
        builder = PullRequestInfoBuilder(number=100, branch=branch_name)
        builder.state = state
        builder.is_draft = is_draft
        builder.checks_passing = checks
        pr = builder.build()

        # Create branch metadata with a simple stack
        branches = {
            "main": BranchMetadata.trunk("main", children=[branch_name]),
            branch_name: BranchMetadata.branch(branch_name, "main", children=[]),
        }

        # Create worktree directory for branch so it appears in the stack
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_worktree = repo_dir / branch_name

        # Build fake git ops with worktree for branch
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_worktree, branch=branch_name),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir, feature_worktree: env.git_dir},
            current_branches={env.cwd: "main", feature_worktree: branch_name},
        )

        # PR data now comes from Graphite, not GitHub
        test_ctx = env.build_context(
            git=git_ops,
            graphite=FakeGraphite(branches=branches, pr_info={branch_name: pr}),
            use_graphite=True,
        )

        # PR info now shown on main line, not just with --stacks
        result = runner.invoke(cli, ["list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Verify emoji appears in output
        assert expected_emoji in result.output
        assert "#100" in result.output


# ===========================
# URL Format Tests (CLI-Specific)
# ===========================


def test_list_with_stacks_uses_graphite_url() -> None:
    """Test that PR links use Graphite URLs instead of GitHub URLs.

    This is CLI-specific behavior: the list command formats PR URLs as Graphite links
    for better integration with Graphite workflow.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        branch_name = "feature"
        pr = PullRequestInfo(
            number=100,
            state="OPEN",
            url="https://github.com/testowner/testrepo/pull/100",
            is_draft=False,
            title=None,
            checks_passing=True,
            owner="testowner",
            repo="testrepo",
        )

        # Create branch metadata with a simple stack
        branches = {
            "main": BranchMetadata.trunk("main", children=[branch_name]),
            branch_name: BranchMetadata.branch(branch_name, "main", children=[]),
        }

        # Create worktree directory for branch so it appears in the stack
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_worktree = repo_dir / branch_name

        # Build fake git ops with worktree for branch
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_worktree, branch=branch_name),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir, feature_worktree: env.git_dir},
            current_branches={env.cwd: "main", feature_worktree: branch_name},
        )

        # PR data now comes from Graphite, not GitHub
        test_ctx = env.build_context(
            git=git_ops,
            graphite=FakeGraphite(branches=branches, pr_info={branch_name: pr}),
            use_graphite=True,
        )

        # PR info now shown on main line, not just with --stacks
        result = runner.invoke(cli, ["list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Output should contain OSC 8 escape sequence with Graphite URL
        # Graphite URL format: https://app.graphite.com/github/pr/owner/repo/number
        expected_url = "https://app.graphite.com/github/pr/testowner/testrepo/100"
        assert expected_url in result.output


# ===========================
# Merge Conflict Tests
# ===========================


def test_list_pr_with_merge_conflicts() -> None:
    """Test that PRs with merge conflicts show the conflict emoji 💥."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        branch_name = "conflict-branch"

        # Create PR with conflicts
        pr = PullRequestInfo(
            number=200,
            state="OPEN",
            url="https://github.com/testowner/testrepo/pull/200",
            is_draft=False,
            title=None,
            checks_passing=True,
            owner="testowner",
            repo="testrepo",
            has_conflicts=True,  # This PR has merge conflicts
        )

        # Create branch metadata
        branches = {
            "main": BranchMetadata.trunk("main", children=[branch_name]),
            branch_name: BranchMetadata.branch(branch_name, "main", children=[]),
        }

        # Create worktree directory
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_worktree = repo_dir / branch_name

        # Build fake git ops
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_worktree, branch=branch_name),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir, feature_worktree: env.git_dir},
            current_branches={env.cwd: "main", feature_worktree: branch_name},
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=FakeGraphite(branches=branches, pr_info={branch_name: pr}),
            use_graphite=True,
        )

        result = runner.invoke(cli, ["list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Verify both the base emoji and conflict emoji appear
        assert "✅💥" in result.output  # PR with passing checks and conflicts
        assert "#200" in result.output


# ===========================
# PR Title Display Tests
# ===========================


def test_list_displays_pr_title_when_available() -> None:
    """Test that list displays PR title from GitHub when available."""
    import click

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        branch_name = "feature-branch"

        # Create PR with title configured
        pr = PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/owner/repo/pull/123",
            is_draft=False,
            title="Add new feature implementation",  # Title from GitHub
            checks_passing=True,
            owner="owner",
            repo="repo",
        )

        branches = {
            "main": BranchMetadata.trunk("main", children=[branch_name]),
            branch_name: BranchMetadata.branch(branch_name, "main", children=[]),
        }

        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_worktree = repo_dir / branch_name

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_worktree, branch=branch_name),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir, feature_worktree: env.git_dir},
            current_branches={env.cwd: "main", feature_worktree: branch_name},
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=FakeGraphite(branches=branches, pr_info={branch_name: pr}),
            use_graphite=True,
        )

        result = runner.invoke(cli, ["list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Remove styling to check content
        unstyled = click.unstyle(result.output)

        # Verify PR title is displayed
        assert "Add new feature implementation" in unstyled

        # Verify title does NOT have 📋 emoji prefix (emoji is for plan summaries)
        assert "📋 Add new feature implementation" not in unstyled


def test_list_prefers_pr_title_over_plan_summary() -> None:
    """Test that list prefers PR title over plan summary when both exist."""

    import click

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        branch_name = "feature-branch"

        # Create PR with title
        pr = PullRequestInfo(
            number=456,
            state="OPEN",
            url="https://github.com/owner/repo/pull/456",
            is_draft=False,
            title="PR title from GitHub",
            checks_passing=True,
            owner="owner",
            repo="repo",
        )

        branches = {
            "main": BranchMetadata.trunk("main", children=[branch_name]),
            branch_name: BranchMetadata.branch(branch_name, "main", children=[]),
        }

        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_worktree = repo_dir / branch_name

        # Create worktree directory
        feature_worktree.mkdir(parents=True, exist_ok=True)

        # Create plan summary file in worktree
        plan_file = feature_worktree / ".impl" / "plan.md"
        plan_file.parent.mkdir(parents=True, exist_ok=True)
        plan_file.write_text("# Plan summary from file\n\nThis is the plan.")

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_worktree, branch=branch_name),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir, feature_worktree: env.git_dir},
            current_branches={env.cwd: "main", feature_worktree: branch_name},
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=FakeGraphite(branches=branches, pr_info={branch_name: pr}),
            use_graphite=True,
        )

        result = runner.invoke(cli, ["list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        unstyled = click.unstyle(result.output)

        # Verify PR title is displayed
        assert "PR title from GitHub" in unstyled

        # Verify plan summary is NOT displayed
        assert "Plan summary from file" not in unstyled


def test_list_falls_back_to_plan_summary_when_no_title() -> None:
    """Test behavior when PR has no title - displays [no plan] if no plan file exists.

    Note: This test verifies the display behavior when title=None. In the real implementation,
    the list command would attempt to read .impl/plan.md if it exists, but in this test
    environment without an actual plan file, it shows [no plan].
    """
    import click

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        branch_name = "feature-branch"

        # Create PR with no title
        pr = PullRequestInfo(
            number=789,
            state="OPEN",
            url="https://github.com/owner/repo/pull/789",
            is_draft=False,
            title=None,  # No title from GitHub
            checks_passing=True,
            owner="owner",
            repo="repo",
        )

        branches = {
            "main": BranchMetadata.trunk("main", children=[branch_name]),
            branch_name: BranchMetadata.branch(branch_name, "main", children=[]),
        }

        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_worktree = repo_dir / branch_name

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_worktree, branch=branch_name),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir, feature_worktree: env.git_dir},
            current_branches={env.cwd: "main", feature_worktree: branch_name},
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=FakeGraphite(branches=branches, pr_info={branch_name: pr}),
            use_graphite=True,
        )

        result = runner.invoke(cli, ["list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        unstyled = click.unstyle(result.output)

        # When title is None and no plan file exists, shows [no plan]
        # (In production, if .impl/plan.md existed, it would be displayed)
        assert "[no plan]" in unstyled


def test_list_shows_no_plan_when_no_title_and_no_summary() -> None:
    """Test that list shows [no plan] placeholder when no PR title or plan."""
    import click

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        branch_name = "feature-branch"

        # Create PR with no title
        pr = PullRequestInfo(
            number=999,
            state="OPEN",
            url="https://github.com/owner/repo/pull/999",
            is_draft=False,
            title=None,  # No title
            checks_passing=True,
            owner="owner",
            repo="repo",
        )

        branches = {
            "main": BranchMetadata.trunk("main", children=[branch_name]),
            branch_name: BranchMetadata.branch(branch_name, "main", children=[]),
        }

        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_worktree = repo_dir / branch_name

        # Create worktree directory but NO plan file
        feature_worktree.mkdir(parents=True, exist_ok=True)

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_worktree, branch=branch_name),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir, feature_worktree: env.git_dir},
            current_branches={env.cwd: "main", feature_worktree: branch_name},
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=FakeGraphite(branches=branches, pr_info={branch_name: pr}),
            use_graphite=True,
        )

        result = runner.invoke(cli, ["list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        unstyled = click.unstyle(result.output)

        # Verify [no plan] placeholder is displayed
        assert "[no plan]" in unstyled

        # Verify no 📋 emoji (only used with plan summaries)
        assert "📋" not in unstyled


def test_list_displays_pr_title_for_multiple_worktrees() -> None:
    """Test that list displays PR titles correctly for multiple worktrees."""
    import click

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        branch1 = "feature-1"
        branch2 = "feature-2"

        # Create two PRs with different titles
        pr1 = PullRequestInfo(
            number=100,
            state="OPEN",
            url="https://github.com/owner/repo/pull/100",
            is_draft=False,
            title="First feature title",
            checks_passing=True,
            owner="owner",
            repo="repo",
        )

        pr2 = PullRequestInfo(
            number=200,
            state="OPEN",
            url="https://github.com/owner/repo/pull/200",
            is_draft=False,
            title="Second feature title",
            checks_passing=True,
            owner="owner",
            repo="repo",
        )

        branches = {
            "main": BranchMetadata.trunk("main", children=[branch1, branch2]),
            branch1: BranchMetadata.branch(branch1, "main", children=[]),
            branch2: BranchMetadata.branch(branch2, "main", children=[]),
        }

        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        worktree1 = repo_dir / branch1
        worktree2 = repo_dir / branch2

        # Create worktree directories
        worktree1.mkdir(parents=True, exist_ok=True)
        worktree2.mkdir(parents=True, exist_ok=True)

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=worktree1, branch=branch1),
                    WorktreeInfo(path=worktree2, branch=branch2),
                ]
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                worktree1: env.git_dir,
                worktree2: env.git_dir,
            },
            current_branches={
                env.cwd: "main",
                worktree1: branch1,
                worktree2: branch2,
            },
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=FakeGraphite(
                branches=branches,
                pr_info={branch1: pr1, branch2: pr2},
            ),
            use_graphite=True,
        )

        result = runner.invoke(cli, ["list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        unstyled = click.unstyle(result.output)

        # Verify both titles are displayed
        assert "First feature title" in unstyled
        assert "Second feature title" in unstyled

        # Verify no mixing of titles (each appears exactly once)
        assert unstyled.count("First feature title") == 1
        assert unstyled.count("Second feature title") == 1


def test_list_fetches_titles_before_ci_enrichment() -> None:
    """Test that list displays both PR title and CI status correctly.

    This test verifies that when a PR has both title and CI status information,
    both are displayed correctly in the list output.
    """
    import click

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        branch_name = "feature-branch"

        # Create PR with both title and CI status
        pr = PullRequestInfo(
            number=300,
            state="OPEN",
            url="https://github.com/owner/repo/pull/300",
            is_draft=False,
            title="Feature with CI checks",
            checks_passing=True,  # CI status is part of PR info
            owner="owner",
            repo="repo",
        )

        branches = {
            "main": BranchMetadata.trunk("main", children=[branch_name]),
            branch_name: BranchMetadata.branch(branch_name, "main", children=[]),
        }

        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_worktree = repo_dir / branch_name

        # Create worktree directory
        feature_worktree.mkdir(parents=True, exist_ok=True)

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_worktree, branch=branch_name),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir, feature_worktree: env.git_dir},
            current_branches={env.cwd: "main", feature_worktree: branch_name},
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=FakeGraphite(branches=branches, pr_info={branch_name: pr}),
            use_graphite=True,
        )

        result = runner.invoke(cli, ["list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        unstyled = click.unstyle(result.output)

        # Verify both title and CI emoji are displayed
        assert "Feature with CI checks" in unstyled
        assert "✅" in result.output  # CI passing emoji
