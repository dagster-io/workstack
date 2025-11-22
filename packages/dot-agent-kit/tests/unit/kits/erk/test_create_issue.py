"""Unit tests for create_issue kit CLI command.

Tests GitHub issue creation with body from stdin and multiple label support.
"""

import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_issue import (
    create_issue,
)

# ============================================================================
# 1. Success Cases (3 tests)
# ============================================================================


def test_create_issue_success() -> None:
    """Test successful issue creation with single label."""
    runner = CliRunner()
    gh_output = "https://github.com/owner/repo/issues/123\n"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout=gh_output,
            stderr="",
        )

        result = runner.invoke(
            create_issue,
            ["Test Issue", "--label", "erk-plan"],
            input="Test body content",
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["issue_number"] == 123
        assert output["issue_url"] == "https://github.com/owner/repo/issues/123"

        # Verify gh command was called correctly
        call_args = mock_run.call_args
        assert call_args[0][0] == [
            "gh",
            "issue",
            "create",
            "--title",
            "Test Issue",
            "--body-file",
            "-",
            "--label",
            "erk-plan",
        ]
        assert call_args[1]["input"] == "Test body content"
        assert call_args[1]["text"] is True


def test_create_issue_no_labels() -> None:
    """Test issue creation without labels."""
    runner = CliRunner()
    gh_output = "https://github.com/owner/repo/issues/456\n"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout=gh_output,
            stderr="",
        )

        result = runner.invoke(create_issue, ["Test Issue"], input="Body content")

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["issue_number"] == 456

        # Verify no --label flags in command
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "--label" not in cmd


def test_create_issue_multiple_labels() -> None:
    """Test issue creation with multiple labels."""
    runner = CliRunner()
    gh_output = "https://github.com/owner/repo/issues/789\n"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout=gh_output,
            stderr="",
        )

        result = runner.invoke(
            create_issue,
            ["Test Issue", "--label", "erk-plan", "--label", "priority-high"],
            input="Body content",
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True

        # Verify both labels in command
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd.count("--label") == 2
        assert "erk-plan" in cmd
        assert "priority-high" in cmd


# ============================================================================
# 2. Stdin Handling Tests (4 tests)
# ============================================================================


def test_create_issue_unicode_content() -> None:
    """Test issue creation with Unicode characters in body."""
    runner = CliRunner()
    gh_output = "https://github.com/owner/repo/issues/100\n"
    unicode_body = "Testing Unicode: 你好 🎉 café"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout=gh_output,
            stderr="",
        )

        result = runner.invoke(
            create_issue,
            ["Test Issue", "--label", "erk-plan"],
            input=unicode_body,
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True

        # Verify Unicode content passed correctly
        call_args = mock_run.call_args
        assert call_args[1]["input"] == unicode_body


def test_create_issue_yaml_frontmatter() -> None:
    """Test issue creation with YAML front matter in body."""
    runner = CliRunner()
    gh_output = "https://github.com/owner/repo/issues/200\n"
    body_with_yaml = """---
erk_plan: true
priority: high
---

# Implementation Plan

This is the plan content."""

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout=gh_output,
            stderr="",
        )

        result = runner.invoke(
            create_issue,
            ["Test Issue", "--label", "erk-plan"],
            input=body_with_yaml,
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True

        # Verify YAML front matter preserved
        call_args = mock_run.call_args
        assert call_args[1]["input"] == body_with_yaml


def test_create_issue_special_characters() -> None:
    """Test issue creation with special characters in body and title."""
    runner = CliRunner()
    gh_output = "https://github.com/owner/repo/issues/300\n"
    special_title = 'Title with "quotes" and `backticks`'
    special_body = """Body with special chars:
- "double quotes"
- 'single quotes'
- `backticks`
- $variables"""

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout=gh_output,
            stderr="",
        )

        result = runner.invoke(
            create_issue,
            [special_title, "--label", "erk-plan"],
            input=special_body,
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True

        # Verify special characters passed correctly
        call_args = mock_run.call_args
        assert call_args[0][0][4] == special_title  # title argument
        assert call_args[1]["input"] == special_body


def test_create_issue_large_body() -> None:
    """Test issue creation with large body content (10,000+ chars)."""
    runner = CliRunner()
    gh_output = "https://github.com/owner/repo/issues/400\n"
    large_body = "x" * 10000  # 10,000 character body

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout=gh_output,
            stderr="",
        )

        result = runner.invoke(
            create_issue,
            ["Test Issue", "--label", "erk-plan"],
            input=large_body,
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True

        # Verify large body passed correctly
        call_args = mock_run.call_args
        assert call_args[1]["input"] == large_body
        assert len(call_args[1]["input"]) == 10000


# ============================================================================
# 3. Error Handling Tests (3 tests)
# ============================================================================


def test_create_issue_gh_not_installed() -> None:
    """Test error handling when gh CLI not installed."""
    runner = CliRunner()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="gh: command not found",
        )

        result = runner.invoke(
            create_issue,
            ["Test Issue", "--label", "erk-plan"],
            input="Body content",
        )

        assert result.exit_code == 1
        assert "Error: gh: command not found" in result.output


def test_create_issue_gh_not_authenticated() -> None:
    """Test error handling when gh not authenticated."""
    runner = CliRunner()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="error: not authenticated",
        )

        result = runner.invoke(
            create_issue,
            ["Test Issue", "--label", "erk-plan"],
            input="Body content",
        )

        assert result.exit_code == 1
        assert "Error: error: not authenticated" in result.output


def test_create_issue_network_error() -> None:
    """Test error handling on network failure."""
    runner = CliRunner()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="error: connection failed",
        )

        result = runner.invoke(
            create_issue,
            ["Test Issue", "--label", "erk-plan"],
            input="Body content",
        )

        assert result.exit_code == 1
        assert "Error: error: connection failed" in result.output


# ============================================================================
# 4. JSON Output Structure Tests (2 tests)
# ============================================================================


def test_json_output_structure_success() -> None:
    """Test JSON output structure on success."""
    runner = CliRunner()
    gh_output = "https://github.com/owner/repo/issues/999\n"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout=gh_output,
            stderr="",
        )

        result = runner.invoke(
            create_issue,
            ["Test Issue", "--label", "erk-plan"],
            input="Body",
        )

        assert result.exit_code == 0
        output = json.loads(result.output)

        # Verify expected keys
        assert "success" in output
        assert "issue_number" in output
        assert "issue_url" in output

        # Verify types
        assert isinstance(output["success"], bool)
        assert isinstance(output["issue_number"], int)
        assert isinstance(output["issue_url"], str)

        # Verify values
        assert output["success"] is True
        assert output["issue_number"] == 999
        assert output["issue_url"] == "https://github.com/owner/repo/issues/999"


def test_json_output_gh_response_parsing() -> None:
    """Test that gh CLI URL response is parsed correctly."""
    runner = CliRunner()
    # Test with different org/repo
    gh_output = "https://github.com/different-org/different-repo/issues/12345\n"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout=gh_output,
            stderr="",
        )

        result = runner.invoke(
            create_issue,
            ["Test Issue"],
            input="Body",
        )

        assert result.exit_code == 0
        output = json.loads(result.output)

        # Verify URL parsing mapped correctly
        assert output["issue_number"] == 12345
        assert output["issue_url"] == "https://github.com/different-org/different-repo/issues/12345"
