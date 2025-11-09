"""Tests for PR info display in list command.

This file tests CLI-specific behavior: emoji rendering, URL formatting, and config handling.
Business logic for PR states is tested in tests/unit/status/test_github_pr_collector.py.
"""

import pytest
from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.global_config_ops import FakeGlobalConfigOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.builders import PullRequestInfoBuilder
from tests.test_utils.repo_setup import SimulatedWorkstackEnv, simulated_workstack_env
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.github_ops import PullRequestInfo
from workstack.core.graphite_ops import BranchMetadata


def _build_context_with_pr(
    env: SimulatedWorkstackEnv,
    branch_name: str,
    pr_info: PullRequestInfo,
    show_pr_info: bool,
) -> WorkstackContext:
    """Helper to build test context with a PR on a branch.

    Args:
        env: SimulatedWorkstackEnv instance
        branch_name: Name of the branch with PR
        pr_info: PR information
        show_pr_info: Whether to show PR info in output

    Returns:
        WorkstackContext configured with PR info
    """
    # Create linked worktree for feature branch
    env.create_linked_worktree(branch_name, branch_name, chdir=False)

    # Build ops from branches with stack relationship
    git_ops, graphite_ops = env.build_ops_from_branches(
        {
            "main": BranchMetadata.main(children=[branch_name], sha="abc123"),
            branch_name: BranchMetadata.branch(
                branch_name, parent="main", sha="def456"
            ),
        },
        current_branch="main",
    )

    # Build fake GitHub ops with PR data
    github_ops = FakeGitHubOps(prs={branch_name: pr_info})

    # Configure show_pr_info
    global_config_ops = FakeGlobalConfigOps(
        workstacks_root=env.workstacks_root,
        use_graphite=True,
        show_pr_info=show_pr_info,
    )

    return WorkstackContext(
        git_ops=git_ops,
        global_config_ops=global_config_ops,
        github_ops=github_ops,
        graphite_ops=graphite_ops,
        shell_ops=FakeShellOps(),
        dry_run=False,
    )


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
    with simulated_workstack_env(runner) as env:
        pr = PullRequestInfo(
            number=42,
            state="OPEN",
            url="https://github.com/owner/repo/pull/42",
            is_draft=False,
            checks_passing=True,
            owner="owner",
            repo="repo",
        )
        test_ctx = _build_context_with_pr(
            env, "feature-branch", pr, show_pr_info=show_pr_info
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
    with simulated_workstack_env(runner) as env:
        # Use builder pattern for PR creation
        builder = PullRequestInfoBuilder(number=100, branch="test-branch")
        builder.state = state
        builder.is_draft = is_draft
        builder.checks_passing = checks
        pr = builder.build()

        test_ctx = _build_context_with_pr(
            env, "test-branch", pr, show_pr_info=True
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
    with simulated_workstack_env(runner) as env:
        pr = PullRequestInfo(
            number=100,
            state="OPEN",
            url="https://github.com/testowner/testrepo/pull/100",
            is_draft=False,
            checks_passing=True,
            owner="testowner",
            repo="testrepo",
        )
        test_ctx = _build_context_with_pr(
            env, "feature", pr, show_pr_info=True
        )

        # PR info now shown on main line, not just with --stacks
        result = runner.invoke(cli, ["list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Output should contain OSC 8 escape sequence with Graphite URL
        # Graphite URL format: https://app.graphite.dev/github/pr/owner/repo/number
        expected_url = "https://app.graphite.dev/github/pr/testowner/testrepo/100"
        assert expected_url in result.output
