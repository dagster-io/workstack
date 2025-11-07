"""Tests for submit_branch kit CLI command."""

import json
import os
import subprocess
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

# Import the command module
from dot_agent_kit.data.kits.gt.kit_cli_commands.gt.submit_branch import (
    PostAnalysisError,
    PostAnalysisResult,
    PreAnalysisError,
    PreAnalysisResult,
    amend_commit,
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

    def test_pre_analysis_with_multiple_commits(self, mock_subprocess: Mock) -> None:
        """Test pre-analysis when multiple commits exist (should squash)."""
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
                # Mock git rev-list --count (3 commits)
                subprocess.CompletedProcess(
                    args=["git", "rev-list", "--count", "main..HEAD"],
                    returncode=0,
                    stdout="3",
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
            assert result.commit_count == 3
            assert result.squashed is True
            assert "Squashed 3 commits" in result.message

    def test_pre_analysis_single_commit(self, mock_subprocess: Mock) -> None:
        """Test pre-analysis when single commit exists (should not squash)."""
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
                # Mock git rev-list --count (1 commit)
                subprocess.CompletedProcess(
                    args=["git", "rev-list", "--count", "main..HEAD"],
                    returncode=0,
                    stdout="1",
                    stderr="",
                ),
                # No gt squash call for single commit
            ]

            result = execute_pre_analysis()

            assert isinstance(result, PreAnalysisResult)
            assert result.success is True
            assert result.commit_count == 1
            assert result.squashed is False
            assert "Single commit, no squash needed" in result.message

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

    def test_pre_analysis_no_commits(self, mock_subprocess: Mock) -> None:
        """Test pre-analysis when no commits exist in branch."""
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
                # Mock git rev-list --count (0 commits)
                subprocess.CompletedProcess(
                    args=["git", "rev-list", "--count", "main..HEAD"],
                    returncode=0,
                    stdout="0",
                    stderr="",
                ),
            ]

            result = execute_pre_analysis()

            assert isinstance(result, PreAnalysisError)
            assert result.success is False
            assert result.error_type == "no_commits"

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
                # Mock git rev-list --count (2 commits, should trigger squash)
                subprocess.CompletedProcess(
                    args=["git", "rev-list", "--count", "main..HEAD"],
                    returncode=0,
                    stdout="2",
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
                    args=["git", "rev-list", "--count", "main..HEAD"],
                    returncode=0,
                    stdout="1",
                    stderr="",
                ),
            ]

            result = runner.invoke(submit_branch, ["pre-analysis"])

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["success"] is True
            assert data["branch_name"] == "feature-branch"
            assert data["parent_branch"] == "main"
            assert data["commit_count"] == 1
            assert data["squashed"] is False

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


class TestAmendCommitWithBackticks:
    """Integration test for amend_commit with special characters.

    This test demonstrates the bug where commit messages containing backticks
    (common in markdown like `/gt:update-pr`) fail due to shell command
    substitution when using the heredoc pattern with sh -c.
    """

    @pytest.fixture
    def git_repo(self) -> Generator[Path]:
        """Create a temporary git repository for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Initialize git repo
            subprocess.run(
                ["git", "init"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Configure git (required for commits)
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            yield repo_path

    def test_amend_commit_with_backticks_direct(self, git_repo: Path) -> None:
        """Test that amend_commit handles markdown backticks correctly when called directly.

        This test verifies that backticks work when calling the function directly from Python.
        Note: The heredoc pattern with <<'EOF' actually handles this correctly because
        the single quotes prevent shell interpretation of the heredoc content.
        """
        # Create initial commit
        test_file = git_repo / "test.txt"
        test_file.write_text("initial", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Prepare message with backticks (like markdown code)
        message_with_backticks = """Add /gt:update-pr command

This adds a new `/gt:update-pr` slash command that uses `git add .` internally.

## Key Changes

- New `/gt:update-pr` command for quick updates
- Uses `gh pr view` to check PR existence
- Runs `git commit -m "Update changes"` automatically"""

        # Change directory to git repo for the function to work
        original_dir = Path.cwd()
        try:
            os.chdir(git_repo)

            # Amend with message containing backticks
            result = amend_commit(message_with_backticks)

            # Should succeed
            assert result is True, "amend_commit should succeed with backticks"

            # Verify commit message was actually updated
            commit_msg_result = subprocess.run(
                ["git", "log", "-1", "--format=%B"],
                cwd=git_repo,
                capture_output=True,
                text=True,
                check=True,
            )
            actual_message = commit_msg_result.stdout.strip()

            # Message should match exactly (including backticks)
            assert actual_message == message_with_backticks, (
                f"Commit message mismatch.\n"
                f"Expected:\n{message_with_backticks}\n\n"
                f"Actual:\n{actual_message}"
            )
        finally:
            os.chdir(original_dir)

    def test_amend_commit_comparison_heredoc_vs_direct(self, git_repo: Path) -> None:
        """Compare heredoc approach vs direct subprocess approach.

        This test demonstrates that while the heredoc pattern works for backticks,
        the direct subprocess approach is simpler, safer, and more maintainable.
        It tests both approaches and validates they produce the same result.
        """
        # Prepare message with various special characters
        complex_message = """Add feature with `backticks`, "quotes", and 'apostrophes'

This message contains:
- Backticks: `/command`, `code`, `git add .`
- Double quotes: "string"
- Single quotes: 'text'
- Dollar signs: $VAR (should not expand)
- Newlines and formatting

## Complex Example

```bash
git commit -m "Update changes"
```"""

        # Create initial commit
        test_file = git_repo / "test.txt"
        test_file.write_text("initial", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        original_dir = Path.cwd()
        try:
            os.chdir(git_repo)

            # Test current heredoc implementation
            result_heredoc = amend_commit(complex_message)
            assert result_heredoc is True, "Heredoc approach should succeed"

            msg_after_heredoc = subprocess.run(
                ["git", "log", "-1", "--format=%B"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()

            # Now test direct subprocess approach (what the fix will use)
            # First, make another commit to amend
            test_file.write_text("second", encoding="utf-8")
            subprocess.run(["git", "add", "."], check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Second commit"],
                check=True,
                capture_output=True,
            )

            # Direct approach (the fix)
            result_direct = subprocess.run(
                ["git", "commit", "--amend", "-m", complex_message],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result_direct.returncode == 0, "Direct approach should succeed"

            msg_after_direct = subprocess.run(
                ["git", "log", "-1", "--format=%B"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()

            # Both should produce identical results
            assert msg_after_heredoc == complex_message, "Heredoc should preserve message exactly"
            assert msg_after_direct == complex_message, "Direct should preserve message exactly"
            assert msg_after_heredoc == msg_after_direct, "Both approaches should be equivalent"

        finally:
            os.chdir(original_dir)
