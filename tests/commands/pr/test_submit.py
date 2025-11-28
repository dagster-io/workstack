"""Tests for erk pr submit command."""

from unittest.mock import patch

from click.testing import CliRunner
from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import (
    PostAnalysisError,
    PostAnalysisResult,
    PreAnalysisError,
)

from erk.cli.commands.pr import pr_group
from erk.core.git.fake import FakeGit
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_submit_success() -> None:
    """Test successful PR submission."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )
        ctx = build_workspace_test_context(env, git=git)

        mock_result = PostAnalysisResult(
            success=True,
            pr_number=123,
            pr_url="https://github.com/owner/repo/pull/123",
            pr_title="Test PR",
            graphite_url="https://app.graphite.dev/github/pr/owner/repo/123",
            branch_name="feature-branch",
            issue_number=None,
            message="Success",
        )

        with patch(
            "erk.cli.commands.pr.submit_cmd.orchestrate_submit_workflow",
            return_value=mock_result,
        ):
            result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code == 0
        assert "https://github.com/owner/repo/pull/123" in result.output
        assert "Graphite:" in result.output


def test_pr_submit_success_without_graphite_url() -> None:
    """Test successful PR submission without Graphite URL."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )
        ctx = build_workspace_test_context(env, git=git)

        mock_result = PostAnalysisResult(
            success=True,
            pr_number=123,
            pr_url="https://github.com/owner/repo/pull/123",
            pr_title="Test PR",
            graphite_url="",  # No Graphite URL
            branch_name="feature-branch",
            issue_number=None,
            message="Success",
        )

        with patch(
            "erk.cli.commands.pr.submit_cmd.orchestrate_submit_workflow",
            return_value=mock_result,
        ):
            result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code == 0
        assert "https://github.com/owner/repo/pull/123" in result.output
        assert "Graphite:" not in result.output  # No Graphite line when URL is empty


def test_pr_submit_fails_on_pre_analysis_error() -> None:
    """Test that command fails when pre-analysis fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )
        ctx = build_workspace_test_context(env, git=git)

        mock_error = PreAnalysisError(
            success=False,
            error_type="no_commits",
            message="No commits found in branch",
            details={"branch_name": "feature-branch"},
        )

        with patch(
            "erk.cli.commands.pr.submit_cmd.orchestrate_submit_workflow",
            return_value=mock_error,
        ):
            result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "No commits found" in result.output


def test_pr_submit_fails_on_gt_not_authenticated() -> None:
    """Test that command shows auth hint when Graphite not authenticated."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        mock_error = PreAnalysisError(
            success=False,
            error_type="gt_not_authenticated",
            message="Graphite CLI (gt) is not authenticated",
            details={"authenticated": False},
        )

        with patch(
            "erk.cli.commands.pr.submit_cmd.orchestrate_submit_workflow",
            return_value=mock_error,
        ):
            result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "gt auth" in result.output


def test_pr_submit_fails_on_gh_not_authenticated() -> None:
    """Test that command shows auth hint when GitHub not authenticated."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        mock_error = PreAnalysisError(
            success=False,
            error_type="gh_not_authenticated",
            message="GitHub CLI (gh) is not authenticated",
            details={"authenticated": False},
        )

        with patch(
            "erk.cli.commands.pr.submit_cmd.orchestrate_submit_workflow",
            return_value=mock_error,
        ):
            result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "gh auth login" in result.output


def test_pr_submit_fails_on_post_analysis_error() -> None:
    """Test that command fails when post-analysis fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )
        ctx = build_workspace_test_context(env, git=git)

        mock_error = PostAnalysisError(
            success=False,
            error_type="submit_failed",
            message="Failed to submit branch",
            details={"branch_name": "feature-branch"},
        )

        with patch(
            "erk.cli.commands.pr.submit_cmd.orchestrate_submit_workflow",
            return_value=mock_error,
        ):
            result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "Failed to submit" in result.output


def test_pr_submit_fails_on_claude_not_available() -> None:
    """Test that command shows install hint when Claude not available."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        mock_error = PostAnalysisError(
            success=False,
            error_type="claude_not_available",
            message="Claude CLI is not available",
            details={"error": "Not found in PATH"},
        )

        with patch(
            "erk.cli.commands.pr.submit_cmd.orchestrate_submit_workflow",
            return_value=mock_error,
        ):
            result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "claude.com/download" in result.output


def test_pr_submit_fails_on_merge_conflicts() -> None:
    """Test that command shows conflict hint when PR has conflicts."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        mock_error = PreAnalysisError(
            success=False,
            error_type="pr_has_conflicts",
            message="PR has merge conflicts",
            details={"branch_name": "feature-branch"},
        )

        with patch(
            "erk.cli.commands.pr.submit_cmd.orchestrate_submit_workflow",
            return_value=mock_error,
        ):
            result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "Resolve conflicts" in result.output


def test_pr_submit_fails_on_empty_parent() -> None:
    """Test that command shows reparent hint when parent is empty."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        mock_error = PostAnalysisError(
            success=False,
            error_type="submit_empty_parent",
            message="Stack contains an empty parent branch",
            details={"branch_name": "feature-branch"},
        )

        with patch(
            "erk.cli.commands.pr.submit_cmd.orchestrate_submit_workflow",
            return_value=mock_error,
        ):
            result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "gt track --parent" in result.output
