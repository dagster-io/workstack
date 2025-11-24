"""Unit tests for format-success-output kit CLI command."""

import json

from click.testing import CliRunner

from erk.data.kits.erk.kit_cli_commands.erk.format_success_output import (
    format_success_output,
)


def test_format_success_output_basic() -> None:
    """Test basic success output formatting."""
    runner = CliRunner()
    result = runner.invoke(
        format_success_output,
        ["--issue-number", "123", "--issue-url", "https://github.com/org/repo/issues/123"],
    )

    assert result.exit_code == 0
    output = result.output

    # Check header line
    assert "✅ GitHub issue created: #123" in output

    # Check URL line
    assert "https://github.com/org/repo/issues/123" in output

    # Check next steps header
    assert "Next steps:" in output

    # Check all four commands
    assert "View Issue: gh issue view 123 --web" in output
    assert "Interactive Execution: erk implement 123" in output
    assert "Dangerous Interactive Execution: erk implement 123 --dangerous" in output
    assert "Yolo One Shot: erk implement 123 --yolo" in output

    # Check JSON metadata footer
    assert "---" in output
    lines = output.strip().split("\n")
    json_line = lines[-1]
    metadata = json.loads(json_line)
    assert metadata["issue_number"] == 123
    assert metadata["issue_url"] == "https://github.com/org/repo/issues/123"
    assert metadata["status"] == "created"


def test_format_success_output_large_issue_number() -> None:
    """Test formatting with large issue number."""
    runner = CliRunner()
    result = runner.invoke(
        format_success_output,
        ["--issue-number", "9999", "--issue-url", "https://github.com/org/repo/issues/9999"],
    )

    assert result.exit_code == 0
    output = result.output

    assert "#9999" in output
    assert "gh issue view 9999" in output
    assert "erk implement 9999" in output

    # Check JSON
    lines = output.strip().split("\n")
    metadata = json.loads(lines[-1])
    assert metadata["issue_number"] == 9999


def test_format_success_output_url_with_query_params() -> None:
    """Test formatting preserves URL with query parameters."""
    runner = CliRunner()
    url = "https://github.com/org/repo/issues/123?comments=1"
    result = runner.invoke(
        format_success_output,
        ["--issue-number", "123", "--issue-url", url],
    )

    assert result.exit_code == 0
    output = result.output

    assert url in output
    lines = output.strip().split("\n")
    metadata = json.loads(lines[-1])
    assert metadata["issue_url"] == url


def test_format_success_output_json_structure() -> None:
    """Test JSON metadata has correct structure and types."""
    runner = CliRunner()
    result = runner.invoke(
        format_success_output,
        ["--issue-number", "456", "--issue-url", "https://github.com/test/test/issues/456"],
    )

    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    json_line = lines[-1]
    metadata = json.loads(json_line)

    # Check keys exist
    assert "issue_number" in metadata
    assert "issue_url" in metadata
    assert "status" in metadata

    # Check types
    assert isinstance(metadata["issue_number"], int)
    assert isinstance(metadata["issue_url"], str)
    assert isinstance(metadata["status"], str)

    # Check values
    assert metadata["issue_number"] == 456
    assert metadata["status"] == "created"


def test_format_success_output_no_placeholders() -> None:
    """Test output contains no placeholder text like <number> or <url>."""
    runner = CliRunner()
    result = runner.invoke(
        format_success_output,
        ["--issue-number", "789", "--issue-url", "https://github.com/org/repo/issues/789"],
    )

    assert result.exit_code == 0
    output = result.output

    # Ensure no placeholders remain
    assert "<number>" not in output
    assert "<url>" not in output
    assert "<issue-url>" not in output


def test_format_success_output_separator_present() -> None:
    """Test output includes separator line before JSON."""
    runner = CliRunner()
    result = runner.invoke(
        format_success_output,
        ["--issue-number", "100", "--issue-url", "https://github.com/org/repo/issues/100"],
    )

    assert result.exit_code == 0
    lines = result.output.strip().split("\n")

    # Find the separator
    assert "---" in lines
    separator_index = lines.index("---")

    # JSON should be after separator (with possible blank line)
    json_line = lines[-1]
    assert separator_index < len(lines) - 1
    assert json_line.startswith("{")


def test_format_success_output_commands_order() -> None:
    """Test commands appear in correct order."""
    runner = CliRunner()
    result = runner.invoke(
        format_success_output,
        ["--issue-number", "500", "--issue-url", "https://github.com/org/repo/issues/500"],
    )

    assert result.exit_code == 0
    lines = result.output.split("\n")

    # Find command lines
    view_line = next(i for i, line in enumerate(lines) if "View Issue:" in line)
    interactive_line = next(i for i, line in enumerate(lines) if "Interactive Execution:" in line)
    dangerous_line = next(
        i for i, line in enumerate(lines) if "Dangerous Interactive Execution:" in line
    )
    yolo_line = next(i for i, line in enumerate(lines) if "Yolo One Shot:" in line)

    # Check order
    assert view_line < interactive_line < dangerous_line < yolo_line
