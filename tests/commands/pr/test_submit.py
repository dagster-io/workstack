"""Tests for erk pr submit command.

The submit command uses Python-first orchestration:
1. execute_pre_analysis() - direct Python call
2. get_diff_context() - direct Python call
3. Claude CLI → /gt:generate-commit-message - only AI call
4. execute_post_analysis() - direct Python call

Tests here verify the orchestration and Claude executor integration.
For unit tests of the underlying functions, see:
packages/dot-agent-kit/tests/unit/kits/gt/test_submit_branch.py
"""

from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk.core.git.fake import FakeGit
from erk.data.kits.gt.kit_cli_commands.gt.submit_branch import (
    DiffContextResult,
    PostAnalysisError,
    PostAnalysisResult,
    PreAnalysisError,
    PreAnalysisResult,
)
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_submit_success() -> None:
    """Test successful PR submission with full orchestration flow."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )
        executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_commit_message="Add feature X\n\n## Summary\nAdded new feature.",
        )
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        # Mock the underlying functions to focus on orchestration testing
        with (
            patch(
                "erk.cli.commands.pr.submit_cmd.execute_pre_analysis"
            ) as mock_pre_analysis,
            patch("erk.cli.commands.pr.submit_cmd.get_diff_context") as mock_get_diff,
            patch(
                "erk.cli.commands.pr.submit_cmd.execute_post_analysis"
            ) as mock_post_analysis,
        ):
            # Configure mocks with correct dataclass fields
            mock_pre_analysis.return_value = PreAnalysisResult(
                success=True,
                branch_name="feature-branch",
                parent_branch="main",
                commit_count=1,
                squashed=False,
                uncommitted_changes_committed=False,
                message="Pre-analysis complete",
            )
            mock_get_diff.return_value = DiffContextResult(
                success=True,
                repo_root="/fake/repo",
                current_branch="feature-branch",
                parent_branch="main",
                diff="diff --git a/file.py b/file.py\n+new line",
            )
            mock_post_analysis.return_value = PostAnalysisResult(
                success=True,
                pr_number=123,
                pr_url="https://github.com/owner/repo/pull/123",
                pr_title="Add feature X",
                graphite_url="https://app.graphite.com/github/pr/owner/repo/123",
                branch_name="feature-branch",
                issue_number=None,
                message="PR submitted",
            )

            result = runner.invoke(pr_group, ["submit"], obj=ctx)

            assert result.exit_code == 0

            # Verify orchestration: each step was called
            mock_pre_analysis.assert_called_once()
            mock_get_diff.assert_called_once()
            mock_post_analysis.assert_called_once()

            # Verify Claude was called for commit message generation
            assert len(executor.executed_commands) == 1
            command, _, dangerous, _ = executor.executed_commands[0]
            assert "/gt:generate-commit-message" in command
            assert dangerous is False

            # Verify post_analysis received the commit message
            call_args = mock_post_analysis.call_args
            assert "Add feature X" in call_args[0][0]  # First positional arg

            # Verify output contains PR URL
            assert "https://github.com/owner/repo/pull/123" in result.output


def test_pr_submit_with_dangerous_flag() -> None:
    """Test PR submission with --dangerous flag passes to Claude executor."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )
        executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_commit_message="Fix bug Y",
        )
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        with (
            patch(
                "erk.cli.commands.pr.submit_cmd.execute_pre_analysis"
            ) as mock_pre_analysis,
            patch("erk.cli.commands.pr.submit_cmd.get_diff_context") as mock_get_diff,
            patch(
                "erk.cli.commands.pr.submit_cmd.execute_post_analysis"
            ) as mock_post_analysis,
        ):
            mock_pre_analysis.return_value = PreAnalysisResult(
                success=True,
                branch_name="feature-branch",
                parent_branch="main",
                commit_count=1,
                squashed=False,
                uncommitted_changes_committed=False,
                message="OK",
            )
            mock_get_diff.return_value = DiffContextResult(
                success=True,
                repo_root="/fake/repo",
                current_branch="feature-branch",
                parent_branch="main",
                diff="diff",
            )
            mock_post_analysis.return_value = PostAnalysisResult(
                success=True,
                pr_number=456,
                pr_url="https://github.com/owner/repo/pull/456",
                pr_title="Fix bug Y",
                graphite_url="",
                branch_name="feature-branch",
                issue_number=None,
                message="OK",
            )

            result = runner.invoke(pr_group, ["submit", "--dangerous"], obj=ctx)

            assert result.exit_code == 0

            # Verify dangerous flag was passed to executor
            assert len(executor.executed_commands) == 1
            _, _, dangerous, _ = executor.executed_commands[0]
            assert dangerous is True


def test_pr_submit_fails_when_claude_not_available() -> None:
    """Test that command fails gracefully when Claude CLI is not available."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        executor = FakeClaudeExecutor(claude_available=False)
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "Claude CLI not found" in result.output


def test_pr_submit_fails_on_pre_analysis_error() -> None:
    """Test that command fails when pre-analysis returns error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        with patch(
            "erk.cli.commands.pr.submit_cmd.execute_pre_analysis"
        ) as mock_pre_analysis:
            mock_pre_analysis.return_value = PreAnalysisError(
                success=False,
                error_type="squash_failed",
                message="Failed to stage changes",
                details={},
            )

            result = runner.invoke(pr_group, ["submit"], obj=ctx)

            assert result.exit_code != 0
            assert "Failed to stage changes" in result.output

            # Claude should NOT have been called
            assert len(executor.executed_commands) == 0


def test_pr_submit_fails_on_empty_commit_message() -> None:
    """Test that command fails when Claude returns empty commit message."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )
        executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_commit_message="",  # Empty commit message
        )
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        with (
            patch(
                "erk.cli.commands.pr.submit_cmd.execute_pre_analysis"
            ) as mock_pre_analysis,
            patch("erk.cli.commands.pr.submit_cmd.get_diff_context") as mock_get_diff,
        ):
            mock_pre_analysis.return_value = PreAnalysisResult(
                success=True,
                branch_name="feature-branch",
                parent_branch="main",
                commit_count=1,
                squashed=False,
                uncommitted_changes_committed=False,
                message="OK",
            )
            mock_get_diff.return_value = DiffContextResult(
                success=True,
                repo_root="/fake/repo",
                current_branch="feature-branch",
                parent_branch="main",
                diff="diff",
            )

            result = runner.invoke(pr_group, ["submit"], obj=ctx)

            assert result.exit_code != 0
            assert "Failed to generate commit message" in result.output


def test_pr_submit_fails_on_post_analysis_error() -> None:
    """Test that command fails when post-analysis returns error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )
        executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_commit_message="Add feature",
        )
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        with (
            patch(
                "erk.cli.commands.pr.submit_cmd.execute_pre_analysis"
            ) as mock_pre_analysis,
            patch("erk.cli.commands.pr.submit_cmd.get_diff_context") as mock_get_diff,
            patch(
                "erk.cli.commands.pr.submit_cmd.execute_post_analysis"
            ) as mock_post_analysis,
        ):
            mock_pre_analysis.return_value = PreAnalysisResult(
                success=True,
                branch_name="feature-branch",
                parent_branch="main",
                commit_count=1,
                squashed=False,
                uncommitted_changes_committed=False,
                message="OK",
            )
            mock_get_diff.return_value = DiffContextResult(
                success=True,
                repo_root="/fake/repo",
                current_branch="feature-branch",
                parent_branch="main",
                diff="diff",
            )
            mock_post_analysis.return_value = PostAnalysisError(
                success=False,
                error_type="submit_failed",
                message="Graphite submit failed: conflicts detected",
                details={},
            )

            result = runner.invoke(pr_group, ["submit"], obj=ctx)

            assert result.exit_code != 0
            assert "Graphite submit failed" in result.output


def test_pr_submit_displays_pr_url() -> None:
    """Test that PR URL is displayed prominently after successful submission."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )
        executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_commit_message="Add feature",
        )
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        with (
            patch(
                "erk.cli.commands.pr.submit_cmd.execute_pre_analysis"
            ) as mock_pre_analysis,
            patch("erk.cli.commands.pr.submit_cmd.get_diff_context") as mock_get_diff,
            patch(
                "erk.cli.commands.pr.submit_cmd.execute_post_analysis"
            ) as mock_post_analysis,
        ):
            mock_pre_analysis.return_value = PreAnalysisResult(
                success=True,
                branch_name="feature-branch",
                parent_branch="main",
                commit_count=1,
                squashed=False,
                uncommitted_changes_committed=False,
                message="OK",
            )
            mock_get_diff.return_value = DiffContextResult(
                success=True,
                repo_root="/fake/repo",
                current_branch="feature-branch",
                parent_branch="main",
                diff="diff",
            )
            mock_post_analysis.return_value = PostAnalysisResult(
                success=True,
                pr_number=789,
                pr_url="https://github.com/owner/repo/pull/789",
                pr_title="Add feature",
                graphite_url="https://app.graphite.com/github/pr/owner/repo/789",
                branch_name="feature-branch",
                issue_number=42,
                message="OK",
            )

            result = runner.invoke(pr_group, ["submit"], obj=ctx)

            assert result.exit_code == 0
            # Verify PR URL is displayed with the 🔗 prefix
            assert "🔗 PR:" in result.output
            assert "https://github.com/owner/repo/pull/789" in result.output
            # Verify issue linkage is mentioned
            assert "#42" in result.output
