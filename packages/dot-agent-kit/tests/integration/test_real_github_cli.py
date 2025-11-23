"""Layer 2 tests: Integration sanity tests for RealDotAgentGitHubCli.

These tests verify that the real implementation correctly wraps subprocess calls
and parses gh CLI output. They use mocking to avoid actual GitHub API calls.

Purpose: Fast validation of subprocess handling and parsing logic.
"""

from unittest.mock import Mock, patch

from dot_agent_kit.integrations.github_cli import RealDotAgentGitHubCli


def test_real_github_cli_create_issue_parses_output_correctly() -> None:
    """Verify RealDotAgentGitHubCli parses gh output correctly."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="https://github.com/owner/repo/issues/123\n",
            stderr="",
        )

        cli = RealDotAgentGitHubCli()
        result = cli.create_issue("Title", "Body", ["label"])

        assert result.success is True
        assert result.issue_number == 123
        assert result.issue_url == "https://github.com/owner/repo/issues/123"


def test_real_github_cli_create_issue_constructs_command_correctly() -> None:
    """Verify RealDotAgentGitHubCli constructs gh command with correct arguments."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="https://github.com/owner/repo/issues/456\n",
            stderr="",
        )

        cli = RealDotAgentGitHubCli()
        cli.create_issue("Test Title", "Test Body", ["label1", "label2"])

        # Verify subprocess.run was called
        assert mock_run.called

        # Verify command structure
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd[0:5] == ["gh", "issue", "create", "--title", "Test Title"]
        assert "--body-file" in cmd
        assert "-" in cmd  # stdin for body
        assert "--label" in cmd
        assert "label1" in cmd
        assert "label2" in cmd

        # Verify body passed via stdin
        assert call_args[1]["input"] == "Test Body"
        assert call_args[1]["text"] is True


def test_real_github_cli_create_issue_handles_command_failure() -> None:
    """Verify error handling when gh command fails."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="error: not authenticated",
        )

        cli = RealDotAgentGitHubCli()
        result = cli.create_issue("Title", "Body", [])

        assert result.success is False
        assert result.issue_number == -1
        assert result.issue_url == ""


def test_real_github_cli_create_issue_handles_malformed_output() -> None:
    """Verify error handling when gh returns unexpected output format."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="unexpected output format\n",
            stderr="",
        )

        cli = RealDotAgentGitHubCli()
        result = cli.create_issue("Title", "Body", [])

        assert result.success is False
        assert result.issue_number == -1
        assert result.issue_url == ""


def test_real_github_cli_create_issue_no_labels() -> None:
    """Verify command structure when no labels provided."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="https://github.com/owner/repo/issues/789\n",
            stderr="",
        )

        cli = RealDotAgentGitHubCli()
        cli.create_issue("Title", "Body", [])

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "--label" not in cmd


def test_real_github_cli_create_issue_unicode_content() -> None:
    """Verify Unicode content is passed correctly to subprocess."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="https://github.com/owner/repo/issues/100\n",
            stderr="",
        )

        cli = RealDotAgentGitHubCli()
        unicode_title = "Title with émojis 🎉"
        unicode_body = "Body with Unicode: 你好"

        cli.create_issue(unicode_title, unicode_body, [])

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert unicode_title in cmd
        assert call_args[1]["input"] == unicode_body


def test_real_github_cli_create_issue_large_body() -> None:
    """Verify large body content is handled correctly."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="https://github.com/owner/repo/issues/200\n",
            stderr="",
        )

        cli = RealDotAgentGitHubCli()
        large_body = "x" * 10000

        cli.create_issue("Title", large_body, [])

        call_args = mock_run.call_args
        assert call_args[1]["input"] == large_body
        assert len(call_args[1]["input"]) == 10000
