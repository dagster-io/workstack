"""Tests for update_pr kit CLI command."""

import json
import subprocess
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

# Import the command module
from dot_agent_kit.data.kits.gt.kit_cli_commands.gt.update_pr import (
    UpdatePRError,
    UpdatePRResult,
    check_pr_exists,
    execute_update_pr,
    get_current_branch,
    has_uncommitted_changes,
    restack_branch,
    stage_and_commit_changes,
    submit_updates,
    update_pr,
)


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_subprocess() -> Mock:
    """Create a mock for subprocess.run."""
    return Mock(spec=subprocess.run)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_current_branch_success(self, mock_subprocess: Mock) -> None:
        """Test get_current_branch returns branch name on success."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "branch", "--show-current"],
                returncode=0,
                stdout="feature-branch",
                stderr="",
            )

            result = get_current_branch()

            assert result == "feature-branch"

    def test_get_current_branch_failure(self, mock_subprocess: Mock) -> None:
        """Test get_current_branch returns None on failure."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "branch", "--show-current"],
                returncode=1,
                stdout="",
                stderr="fatal: not a git repository",
            )

            result = get_current_branch()

            assert result is None

    def test_check_pr_exists_success(self, mock_subprocess: Mock) -> None:
        """Test check_pr_exists returns PR info when PR exists."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["gh", "pr", "view", "--json", "number,url"],
                returncode=0,
                stdout='{"number": 123, "url": "https://github.com/owner/repo/pull/123"}',
                stderr="",
            )

            result = check_pr_exists()

            assert result == (123, "https://github.com/owner/repo/pull/123")

    def test_check_pr_exists_no_pr(self, mock_subprocess: Mock) -> None:
        """Test check_pr_exists returns None when no PR exists."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["gh", "pr", "view", "--json", "number,url"],
                returncode=1,
                stdout="",
                stderr="no pull requests found",
            )

            result = check_pr_exists()

            assert result is None

    def test_has_uncommitted_changes_true(self, mock_subprocess: Mock) -> None:
        """Test has_uncommitted_changes returns True when changes exist."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "status", "--porcelain"],
                returncode=0,
                stdout=" M file.txt\n",
                stderr="",
            )

            result = has_uncommitted_changes()

            assert result is True

    def test_has_uncommitted_changes_false(self, mock_subprocess: Mock) -> None:
        """Test has_uncommitted_changes returns False when no changes exist."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "status", "--porcelain"],
                returncode=0,
                stdout="",
                stderr="",
            )

            result = has_uncommitted_changes()

            assert result is False

    def test_stage_and_commit_changes_success(self, mock_subprocess: Mock) -> None:
        """Test stage_and_commit_changes succeeds when both commands succeed."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                # Mock git add .
                subprocess.CompletedProcess(
                    args=["git", "add", "."],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock git commit
                subprocess.CompletedProcess(
                    args=["git", "commit", "-m", "Update changes"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
            ]

            result = stage_and_commit_changes()

            assert result is True

    def test_stage_and_commit_changes_add_fails(self, mock_subprocess: Mock) -> None:
        """Test stage_and_commit_changes fails when git add fails."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "add", "."],
                returncode=1,
                stdout="",
                stderr="fatal: error",
            )

            result = stage_and_commit_changes()

            assert result is False

    def test_stage_and_commit_changes_commit_fails(self, mock_subprocess: Mock) -> None:
        """Test stage_and_commit_changes fails when git commit fails."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                # Mock git add . (succeeds)
                subprocess.CompletedProcess(
                    args=["git", "add", "."],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock git commit (fails)
                subprocess.CompletedProcess(
                    args=["git", "commit", "-m", "Update changes"],
                    returncode=1,
                    stdout="",
                    stderr="nothing to commit",
                ),
            ]

            result = stage_and_commit_changes()

            assert result is False

    def test_restack_branch_success(self, mock_subprocess: Mock) -> None:
        """Test restack_branch returns True on success."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["gt", "restack", "--no-interactive"],
                returncode=0,
                stdout="",
                stderr="",
            )

            result = restack_branch()

            assert result is True

    def test_restack_branch_failure(self, mock_subprocess: Mock) -> None:
        """Test restack_branch returns False on failure (conflicts)."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["gt", "restack", "--no-interactive"],
                returncode=1,
                stdout="",
                stderr="Conflicts detected",
            )

            result = restack_branch()

            assert result is False

    def test_submit_updates_success(self, mock_subprocess: Mock) -> None:
        """Test submit_updates returns True on success."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["gt", "submit"],
                returncode=0,
                stdout="",
                stderr="",
            )

            result = submit_updates()

            assert result is True

    def test_submit_updates_failure(self, mock_subprocess: Mock) -> None:
        """Test submit_updates returns False on failure."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["gt", "submit"],
                returncode=1,
                stdout="",
                stderr="Failed to submit",
            )

            result = submit_updates()

            assert result is False


class TestExecuteUpdatePR:
    """Tests for execute_update_pr workflow."""

    def test_success_with_uncommitted_changes(self, mock_subprocess: Mock) -> None:
        """Test successful workflow with uncommitted changes."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                # Mock get_current_branch
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                # Mock check_pr_exists
                subprocess.CompletedProcess(
                    args=["gh", "pr", "view", "--json", "number,url"],
                    returncode=0,
                    stdout='{"number": 235, "url": "https://github.com/owner/repo/pull/235"}',
                    stderr="",
                ),
                # Mock has_uncommitted_changes
                subprocess.CompletedProcess(
                    args=["git", "status", "--porcelain"],
                    returncode=0,
                    stdout=" M file.txt\n",
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
                    args=["git", "commit", "-m", "Update changes"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock gt restack
                subprocess.CompletedProcess(
                    args=["gt", "restack", "--no-interactive"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock gt submit
                subprocess.CompletedProcess(
                    args=["gt", "submit"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
            ]

            result = execute_update_pr()

            assert isinstance(result, UpdatePRResult)
            assert result.success is True
            assert result.pr_number == 235
            assert result.pr_url == "https://github.com/owner/repo/pull/235"
            assert result.branch_name == "feature-branch"
            assert result.had_changes is True
            assert "Committed changes" in result.message

    def test_success_without_uncommitted_changes(self, mock_subprocess: Mock) -> None:
        """Test successful workflow without uncommitted changes."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                # Mock get_current_branch
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                # Mock check_pr_exists
                subprocess.CompletedProcess(
                    args=["gh", "pr", "view", "--json", "number,url"],
                    returncode=0,
                    stdout='{"number": 235, "url": "https://github.com/owner/repo/pull/235"}',
                    stderr="",
                ),
                # Mock has_uncommitted_changes (no changes)
                subprocess.CompletedProcess(
                    args=["git", "status", "--porcelain"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock gt restack
                subprocess.CompletedProcess(
                    args=["gt", "restack", "--no-interactive"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock gt submit
                subprocess.CompletedProcess(
                    args=["gt", "submit"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
            ]

            result = execute_update_pr()

            assert isinstance(result, UpdatePRResult)
            assert result.success is True
            assert result.had_changes is False
            assert "No uncommitted changes" in result.message

    def test_error_no_pr(self, mock_subprocess: Mock) -> None:
        """Test error when no PR exists."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                # Mock get_current_branch
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                # Mock check_pr_exists (no PR)
                subprocess.CompletedProcess(
                    args=["gh", "pr", "view", "--json", "number,url"],
                    returncode=1,
                    stdout="",
                    stderr="no pull requests found",
                ),
            ]

            result = execute_update_pr()

            assert isinstance(result, UpdatePRError)
            assert result.success is False
            assert result.error_type == "no_pr"
            assert "No PR associated" in result.message

    def test_error_commit_failed(self, mock_subprocess: Mock) -> None:
        """Test error when commit fails."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                # Mock get_current_branch
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                # Mock check_pr_exists
                subprocess.CompletedProcess(
                    args=["gh", "pr", "view", "--json", "number,url"],
                    returncode=0,
                    stdout='{"number": 235, "url": "https://github.com/owner/repo/pull/235"}',
                    stderr="",
                ),
                # Mock has_uncommitted_changes
                subprocess.CompletedProcess(
                    args=["git", "status", "--porcelain"],
                    returncode=0,
                    stdout=" M file.txt\n",
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
                    args=["git", "commit", "-m", "Update changes"],
                    returncode=1,
                    stdout="",
                    stderr="nothing to commit",
                ),
            ]

            result = execute_update_pr()

            assert isinstance(result, UpdatePRError)
            assert result.success is False
            assert result.error_type == "commit_failed"

    def test_error_restack_failed(self, mock_subprocess: Mock) -> None:
        """Test error when restack fails (conflicts)."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                # Mock get_current_branch
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                # Mock check_pr_exists
                subprocess.CompletedProcess(
                    args=["gh", "pr", "view", "--json", "number,url"],
                    returncode=0,
                    stdout='{"number": 235, "url": "https://github.com/owner/repo/pull/235"}',
                    stderr="",
                ),
                # Mock has_uncommitted_changes (no changes)
                subprocess.CompletedProcess(
                    args=["git", "status", "--porcelain"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock gt restack (fails with conflicts)
                subprocess.CompletedProcess(
                    args=["gt", "restack", "--no-interactive"],
                    returncode=1,
                    stdout="",
                    stderr="Conflicts detected",
                ),
            ]

            result = execute_update_pr()

            assert isinstance(result, UpdatePRError)
            assert result.success is False
            assert result.error_type == "restack_failed"
            assert "Conflicts occurred" in result.message

    def test_error_submit_failed(self, mock_subprocess: Mock) -> None:
        """Test error when submit fails."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                # Mock get_current_branch
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                # Mock check_pr_exists
                subprocess.CompletedProcess(
                    args=["gh", "pr", "view", "--json", "number,url"],
                    returncode=0,
                    stdout='{"number": 235, "url": "https://github.com/owner/repo/pull/235"}',
                    stderr="",
                ),
                # Mock has_uncommitted_changes (no changes)
                subprocess.CompletedProcess(
                    args=["git", "status", "--porcelain"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock gt restack
                subprocess.CompletedProcess(
                    args=["gt", "restack", "--no-interactive"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                # Mock gt submit (fails)
                subprocess.CompletedProcess(
                    args=["gt", "submit"],
                    returncode=1,
                    stdout="",
                    stderr="Failed to submit",
                ),
            ]

            result = execute_update_pr()

            assert isinstance(result, UpdatePRError)
            assert result.success is False
            assert result.error_type == "submit_failed"


class TestUpdatePRCommand:
    """Tests for update_pr CLI command."""

    def test_command_success(self, runner: CliRunner, mock_subprocess: Mock) -> None:
        """Test command returns valid JSON on success."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=["gh", "pr", "view", "--json", "number,url"],
                    returncode=0,
                    stdout='{"number": 235, "url": "https://github.com/owner/repo/pull/235"}',
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=["git", "status", "--porcelain"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=["gt", "restack", "--no-interactive"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=["gt", "submit"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
            ]

            result = runner.invoke(update_pr)

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["success"] is True
            assert data["pr_number"] == 235
            assert data["branch_name"] == "feature-branch"

    def test_command_error(self, runner: CliRunner, mock_subprocess: Mock) -> None:
        """Test command returns error JSON and exit code 1 on failure."""
        with patch("subprocess.run", mock_subprocess) as mock_run:
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=["git", "branch", "--show-current"],
                    returncode=0,
                    stdout="feature-branch",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=["gh", "pr", "view", "--json", "number,url"],
                    returncode=1,
                    stdout="",
                    stderr="no pull requests found",
                ),
            ]

            result = runner.invoke(update_pr)

            assert result.exit_code == 1
            data = json.loads(result.output)
            assert data["success"] is False
            assert data["error_type"] == "no_pr"
