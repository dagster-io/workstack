"""Tests for PR info display in list command.

This file tests CLI-specific behavior: emoji rendering, URL formatting, and config handling.
Business logic for PR states is tested in tests/unit/status/test_github_pr_collector.py.
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.global_config_ops import FakeGlobalConfigOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.builders import PullRequestInfoBuilder
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.github_ops import PullRequestInfo
from workstack.core.gitops import WorktreeInfo


def _setup_test_with_pr(
    branch_name: str,
    pr_info: PullRequestInfo,
    show_pr_info: bool,
) -> tuple[Path, Path, Path, WorkstackContext]:
    """Helper to set up a test environment with a PR on a branch.

    Returns:
        Tuple of (cwd, workstacks_root, feature_worktree, test_ctx)
    """
    # Set up isolated environment
    cwd = Path.cwd()
    workstacks_root = cwd / "workstacks"

    # Create git repo structure
    git_dir = Path(".git")
    git_dir.mkdir()

    # Create graphite cache with a simple stack
    graphite_cache = {
        "branches": [
            ("main", {"validationResult": "TRUNK", "children": [branch_name]}),
            (branch_name, {"parentBranchName": "main", "children": []}),
        ]
    }
    (git_dir / ".graphite_cache_persist").write_text(json.dumps(graphite_cache))

    # Create worktree directory for branch so it appears in the stack
    repo_name = cwd.name
    workstacks_dir = workstacks_root / repo_name
    feature_worktree = workstacks_dir / branch_name
    feature_worktree.mkdir(parents=True)

    # Build fake git ops with worktree for branch
    git_ops = FakeGitOps(
        worktrees={
            cwd: [
                WorktreeInfo(path=cwd, branch="main"),
                WorktreeInfo(path=feature_worktree, branch=branch_name),
            ]
        },
        git_common_dirs={cwd: git_dir, feature_worktree: git_dir},
        current_branches={cwd: "main", feature_worktree: branch_name},
    )

    # Build fake GitHub ops with PR data
    github_ops = FakeGitHubOps(prs={branch_name: pr_info})

    # Configure show_pr_info
    global_config_ops = FakeGlobalConfigOps(
        workstacks_root=workstacks_root,
        use_graphite=True,
        show_pr_info=show_pr_info,
    )

    graphite_ops = FakeGraphiteOps()

    test_ctx = WorkstackContext(
        git_ops=git_ops,
        global_config_ops=global_config_ops,
        github_ops=github_ops,
        graphite_ops=graphite_ops,
        shell_ops=FakeShellOps(),
        dry_run=False,
    )

    return cwd, workstacks_root, feature_worktree, test_ctx


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
    with runner.isolated_filesystem():
        pr = PullRequestInfo(
            number=42,
            state="OPEN",
            url="https://github.com/owner/repo/pull/42",
            is_draft=False,
            checks_passing=True,
            owner="owner",
            repo="repo",
        )
        _cwd, _workstacks_root, _feature_worktree, test_ctx = _setup_test_with_pr(
            "feature-branch", pr, show_pr_info=show_pr_info
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
    with runner.isolated_filesystem():
        # Use builder pattern for PR creation
        builder = PullRequestInfoBuilder(number=100, branch="test-branch")
        builder.state = state
        builder.is_draft = is_draft
        builder.checks_passing = checks
        pr = builder.build()

        _cwd, _workstacks_root, _feature_worktree, test_ctx = _setup_test_with_pr(
            "test-branch", pr, show_pr_info=True
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
    with runner.isolated_filesystem():
        pr = PullRequestInfo(
            number=100,
            state="OPEN",
            url="https://github.com/testowner/testrepo/pull/100",
            is_draft=False,
            checks_passing=True,
            owner="testowner",
            repo="testrepo",
        )
        _cwd, _workstacks_root, _feature_worktree, test_ctx = _setup_test_with_pr(
            "feature", pr, show_pr_info=True
        )

        # PR info now shown on main line, not just with --stacks
        result = runner.invoke(cli, ["list"], obj=test_ctx)
        assert result.exit_code == 0, result.output

        # Output should contain OSC 8 escape sequence with Graphite URL
        # Graphite URL format: https://app.graphite.dev/github/pr/owner/repo/number
        expected_url = "https://app.graphite.dev/github/pr/testowner/testrepo/100"
        assert expected_url in result.output
