"""Tests for submit_branch kit CLI command."""

import json
import subprocess
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

# Import the command module
from dot_agent_kit.data.kits.gt.kit_cli_commands.gt.submit_branch import (
    PostAnalysisError,
    PostAnalysisResult,
    PreAnalysisError,
    PreAnalysisResult,
    execute_post_analysis,
    execute_pre_analysis,
    submit_branch,
)


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_subprocess() -> Mock:
    """Create a mock for subprocess.run."""
    return Mock(spec=subprocess.run)


class TestPreAnalysisExecution:
    """Tests for pre-analysis phase execution logic."""

    def test_pre_analysis_with_uncommitted_changes(self, mock_subprocess: Mock) -> None:
        """Test pre-analysis when uncommitted changes exist."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            # Mock git branch --show-current
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                # Mock gt parent
                subprocess.CompletedProcess(
                    args=["gt", "parent"],
                    returncode=0,
                    stdout="main",
                    stderr="",
                ),
                # Mock git status --porcelain (has changes)
                subprocess.CompletedProcess(
                    args=["git", "status", "--porcelain"],
                    returncode=0,
                    stdout="M file.py\nA new_file.py",
                    stderr="",
                ),
                # Mock git add .
                subprocess.CompletedProcess(
                    args=["git", "add", "."],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock git commit
                subprocess.CompletedProcess(
                    args=["git", "commit", "-m", "WIP: Prepare for submission"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock gt squash
                subprocess.CompletedProcess(
                    args=["gt", "squash"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
            ]

            result = execute_pre_analysis()

            assert isinstance(result, PreAnalysisResult)
            assert result.success is True
            assert result.branch_name == "feature-branch"
            assert result.parent_branch == "main"
            assert result.had_uncommitted_changes is True
            assert "Committed uncommitted changes" in result.message

    def test_pre_analysis_no_uncommitted_changes(self, mock_subprocess: Mock) -> None:
        """Test pre-analysis when no uncommitted changes exist."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                # Mock git branch --show-current
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                # Mock gt parent
                subprocess.CompletedProcess(
                    args=["gt", "parent"],
                    returncode=0,
                    stdout="main",
                    stderr="",
                ),
                # Mock git status --porcelain (no changes)
                subprocess.CompletedProcess(
                    args=["git", "status", "--porcelain"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock gt squash
                subprocess.CompletedProcess(
                    args=["gt", "squash"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
            ]

            result = execute_pre_analysis()

            assert isinstance(result, PreAnalysisResult)
            assert result.success is True
            assert result.had_uncommitted_changes is False
            assert "Squashed commits" in result.message

    def test_pre_analysis_no_branch(self, mock_subprocess: Mock) -> None:
        """Test pre-analysis when current branch cannot be determined."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "branch", "--show-current"],
                returncode=1,
                stdout="",
                stderr="fatal: not a git repository",
            )

            result = execute_pre_analysis()

            assert isinstance(result, PreAnalysisError)
            assert result.success is False
            assert result.error_type == "no_branch"

    def test_pre_analysis_no_parent(self, mock_subprocess: Mock) -> None:
        """Test pre-analysis when parent branch cannot be determined."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                # Mock git branch --show-current
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                # Mock gt parent (fails)
                subprocess.CompletedProcess(
                    args=["gt", "parent"],
                    returncode=1,
                    stdout="",
                    stderr="No parent found",
                ),
            ]

            result = execute_pre_analysis()

            assert isinstance(result, PreAnalysisError)
            assert result.success is False
            assert result.error_type == "no_parent"

    def test_pre_analysis_commit_fails(self, mock_subprocess: Mock) -> None:
        """Test pre-analysis when git commit fails."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                # Mock git branch --show-current
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                # Mock gt parent
                subprocess.CompletedProcess(
                    args=["gt", "parent"],
                    returncode=0,
                    stdout="main",
                    stderr="",
                ),
                # Mock git status --porcelain (has changes)
                subprocess.CompletedProcess(
                    args=["git", "status", "--porcelain"],
                    returncode=0,
                    stdout="M file.py",
                    stderr="",
                ),
                # Mock git add .
                subprocess.CompletedProcess(
                    args=["git", "add", "."],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock git commit (fails)
                subprocess.CompletedProcess(
                    args=["git", "commit", "-m", "WIP: Prepare for submission"],
                    returncode=1,
                    stdout="",
                    stderr="Nothing to commit",
                ),
            ]

            result = execute_pre_analysis()

            assert isinstance(result, PreAnalysisError)
            assert result.success is False
            assert result.error_type == "commit_failed"

    def test_pre_analysis_squash_fails(self, mock_subprocess: Mock) -> None:
        """Test pre-analysis when gt squash fails."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                # Mock git branch --show-current
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                # Mock gt parent
                subprocess.CompletedProcess(
                    args=["gt", "parent"],
                    returncode=0,
                    stdout="main",
                    stderr="",
                ),
                # Mock git status --porcelain (no changes)
                subprocess.CompletedProcess(
                    args=["git", "status", "--porcelain"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock gt squash (fails)
                subprocess.CompletedProcess(
                    args=["gt", "squash"],
                    returncode=1,
                    stdout="",
                    stderr="Cannot squash",
                ),
            ]

            result = execute_pre_analysis()

            assert isinstance(result, PreAnalysisError)
            assert result.success is False
            assert result.error_type == "squash_failed"


class TestPostAnalysisExecution:
    """Tests for post-analysis phase execution logic."""

    def test_post_analysis_creates_pr(self, mock_subprocess: Mock) -> None:
        """Test post-analysis when submitting creates new PR."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                # Mock git branch --show-current
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                # Mock git commit --amend (via sh -c)
                subprocess.CompletedProcess(
                    args=["sh", "-c"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock gt submit
                subprocess.CompletedProcess(
                    args=["gt", "submit", "--publish", "--no-interactive", "--restack"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock gh pr view (no PR exists)
                subprocess.CompletedProcess(
                    args=["gh", "pr", "view", "--json", "number,url"],
                    returncode=1,
                    stdout="",
                    stderr="no pull requests found",
                ),
            ]

            result = execute_post_analysis(
                commit_message="feat: add feature\n\nDetailed description",
                pr_title="feat: add feature",
                pr_body="Detailed description",
            )

            assert isinstance(result, PostAnalysisResult)
            assert result.success is True
            assert result.pr_number is None
            assert "PR created (number pending)" in result.message

    def test_post_analysis_updates_existing_pr(self, mock_subprocess: Mock) -> None:
        """Test post-analysis when PR already exists and needs updating."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                # Mock git branch --show-current
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                # Mock git commit --amend (via sh -c)
                subprocess.CompletedProcess(
                    args=["sh", "-c"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock gt submit
                subprocess.CompletedProcess(
                    args=["gt", "submit", "--publish", "--no-interactive", "--restack"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock gh pr view (PR exists)
                subprocess.CompletedProcess(
                    args=["gh", "pr", "view", "--json", "number,url"],
                    returncode=0,
                    stdout='{"number": 123, "url": "https://github.com/owner/repo/pull/123"}',
                    stderr="",
                ),
                # Mock gh pr edit
                subprocess.CompletedProcess(
                    args=[
                        "gh",
                        "pr",
                        "edit",
                        "--title",
                        "feat: add feature",
                        "--body",
                        "Detailed description",
                    ],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
            ]

            result = execute_post_analysis(
                commit_message="feat: add feature\n\nDetailed description",
                pr_title="feat: add feature",
                pr_body="Detailed description",
            )

            assert isinstance(result, PostAnalysisResult)
            assert result.success is True
            assert result.pr_number == 123
            assert result.pr_url == "https://github.com/owner/repo/pull/123"
            assert "Updated PR #123" in result.message

    def test_post_analysis_amend_fails(self, mock_subprocess: Mock) -> None:
        """Test post-analysis when git commit --amend fails."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                # Mock git branch --show-current
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                # Mock git commit --amend (fails)
                subprocess.CompletedProcess(
                    args=["sh", "-c"],
                    returncode=1,
                    stdout="",
                    stderr="Cannot amend",
                ),
            ]

            result = execute_post_analysis(
                commit_message="feat: add feature\n\nDetailed description",
                pr_title="feat: add feature",
                pr_body="Detailed description",
            )

            assert isinstance(result, PostAnalysisError)
            assert result.success is False
            assert result.error_type == "amend_failed"

    def test_post_analysis_submit_fails(self, mock_subprocess: Mock) -> None:
        """Test post-analysis when gt submit fails."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                # Mock git branch --show-current
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                # Mock git commit --amend
                subprocess.CompletedProcess(
                    args=["sh", "-c"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock gt submit (fails)
                subprocess.CompletedProcess(
                    args=["gt", "submit", "--publish", "--no-interactive", "--restack"],
                    returncode=1,
                    stdout="",
                    stderr="Branch has been updated remotely",
                ),
            ]

            result = execute_post_analysis(
                commit_message="feat: add feature\n\nDetailed description",
                pr_title="feat: add feature",
                pr_body="Detailed description",
            )

            assert isinstance(result, PostAnalysisError)
            assert result.success is False
            assert result.error_type == "submit_failed"

    def test_post_analysis_pr_update_fails(self, mock_subprocess: Mock) -> None:
        """Test post-analysis when gh pr edit fails."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                # Mock git branch --show-current
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                # Mock git commit --amend
                subprocess.CompletedProcess(
                    args=["sh", "-c"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock gt submit
                subprocess.CompletedProcess(
                    args=["gt", "submit", "--publish", "--no-interactive", "--restack"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock gh pr view (PR exists)
                subprocess.CompletedProcess(
                    args=["gh", "pr", "view", "--json", "number,url"],
                    returncode=0,
                    stdout='{"number": 123, "url": "https://github.com/owner/repo/pull/123"}',
                    stderr="",
                ),
                # Mock gh pr edit (fails)
                subprocess.CompletedProcess(
                    args=[
                        "gh",
                        "pr",
                        "edit",
                        "--title",
                        "feat: add feature",
                        "--body",
                        "Detailed description",
                    ],
                    returncode=1,
                    stdout="",
                    stderr="PR not found",
                ),
            ]

            result = execute_post_analysis(
                commit_message="feat: add feature\n\nDetailed description",
                pr_title="feat: add feature",
                pr_body="Detailed description",
            )

            assert isinstance(result, PostAnalysisError)
            assert result.success is False
            assert result.error_type == "pr_update_failed"


class TestPreAnalysisCommand:
    """Tests for pre-analysis CLI command."""

    def test_pre_analysis_command_success(self, runner: CliRunner, mock_subprocess: Mock) -> None:
        """Test pre-analysis command returns valid JSON on success."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=["gt", "parent"],
                    returncode=0,
                    stdout="main",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=["git", "status", "--porcelain"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=["gt", "squash"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
            ]

            result = runner.invoke(submit_branch, ["pre-analysis"])

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["success"] is True
            assert data["branch_name"] == "feature-branch"
            assert data["parent_branch"] == "main"

    def test_pre_analysis_command_error(self, runner: CliRunner, mock_subprocess: Mock) -> None:
        """Test pre-analysis command returns error JSON and exit code 1 on failure."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "branch", "--show-current"],
                returncode=1,
                stdout="",
                stderr="fatal: not a git repository",
            )

            result = runner.invoke(submit_branch, ["pre-analysis"])

            assert result.exit_code == 1
            data = json.loads(result.output)
            assert data["success"] is False
            assert data["error_type"] == "no_branch"


class TestPostAnalysisCommand:
    """Tests for post-analysis CLI command."""

    def test_post_analysis_command_success(self, runner: CliRunner, mock_subprocess: Mock) -> None:
        """Test post-analysis command returns valid JSON on success."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=["sh", "-c"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=["gt", "submit", "--publish", "--no-interactive", "--restack"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=["gh", "pr", "view", "--json", "number,url"],
                    returncode=0,
                    stdout='{"number": 123, "url": "https://github.com/owner/repo/pull/123"}',
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=["gh", "pr", "edit"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
            ]

            result = runner.invoke(
                submit_branch,
                [
                    "post-analysis",
                    "--commit-message",
                    "feat: add feature\n\nDetailed description",
                    "--pr-title",
                    "feat: add feature",
                    "--pr-body",
                    "Detailed description",
                ],
            )

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["success"] is True
            assert data["pr_number"] == 123

    def test_post_analysis_command_error(self, runner: CliRunner, mock_subprocess: Mock) -> None:
        """Test post-analysis command returns error JSON and exit code 1 on failure."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=["sh", "-c"],
                    returncode=1,
                    stdout="",
                    stderr="Cannot amend",
                ),
            ]

            result = runner.invoke(
                submit_branch,
                [
                    "post-analysis",
                    "--commit-message",
                    "feat: add feature",
                    "--pr-title",
                    "feat: add feature",
                    "--pr-body",
                    "Detailed description",
                ],
            )

            assert result.exit_code == 1
            data = json.loads(result.output)
            assert data["success"] is False
            assert data["error_type"] == "amend_failed"

    def test_post_analysis_command_requires_arguments(self, runner: CliRunner) -> None:
        """Test post-analysis command requires all arguments."""
        result = runner.invoke(submit_branch, ["post-analysis"])

        assert result.exit_code != 0
        assert "Error" in result.output or "Missing option" in result.output
