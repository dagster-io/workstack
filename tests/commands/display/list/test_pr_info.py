"""Tests for PR info display in list command.

This file tests CLI-specific behavior: emoji rendering, URL formatting, and config handling.
Business logic for PR states is tested in tests/unit/status/test_github_pr_collector.py.
"""

import pytest
from click.testing import CliRunner

from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.test_utils.builders import PullRequestInfoBuilder
from tests.test_utils.env_helpers import pure_workstack_env
from workstack.cli.cli import cli
from workstack.core.branch_metadata import BranchMetadata
from workstack.core.github_ops import PullRequestInfo
from workstack.core.gitops import WorktreeInfo

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
    with pure_workstack_env(runner) as env:
        branch_name = "feature-branch"
        pr = PullRequestInfo(
            number=42,
            state="OPEN",
            url="https://github.com/owner/repo/pull/42",
            is_draft=False,
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
        workstacks_dir = env.workstacks_root / repo_name
        feature_worktree = workstacks_dir / branch_name

        # Build fake git ops with worktree for branch
        git_ops = FakeGitOps(
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
            git_ops=git_ops,
            graphite_ops=FakeGraphiteOps(branches=branches, pr_info={branch_name: pr}),
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
        ("OPEN", False, None, "◯"),  # Open PR with no checks
        ("OPEN", True, None, "🚧"),  # Draft PR
        ("MERGED", False, True, "🟣"),  # Merged PR
        ("CLOSED", False, None, "⭕"),  # Closed (not merged) PR
    ],
)
def test_list_pr_emoji_mapping(
    state: str, is_draft: bool, checks: bool | None, expected_emoji: str
) -> None:
    """Verify PR state → emoji mapping for all cases.

    This test covers all emoji rendering logic in a single parametrized test.
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
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
        workstacks_dir = env.workstacks_root / repo_name
        feature_worktree = workstacks_dir / branch_name

        # Build fake git ops with worktree for branch
        git_ops = FakeGitOps(
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
            git_ops=git_ops,
            graphite_ops=FakeGraphiteOps(branches=branches, pr_info={branch_name: pr}),
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
    with pure_workstack_env(runner) as env:
        branch_name = "feature"
        pr = PullRequestInfo(
            number=100,
            state="OPEN",
            url="https://github.com/testowner/testrepo/pull/100",
            is_draft=False,
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
        workstacks_dir = env.workstacks_root / repo_name
        feature_worktree = workstacks_dir / branch_name

        # Build fake git ops with worktree for branch
        git_ops = FakeGitOps(
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
            git_ops=git_ops,
            graphite_ops=FakeGraphiteOps(branches=branches, pr_info={branch_name: pr}),
            use_graphite=True,
        )

        # PR info now shown on main line, not just with --stacks
        result = runner.invoke(cli, ["list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Output should contain OSC 8 escape sequence with Graphite URL
        # Graphite URL format: https://app.graphite.com/github/pr/owner/repo/number
        expected_url = "https://app.graphite.com/github/pr/testowner/testrepo/100"
        assert expected_url in result.output
