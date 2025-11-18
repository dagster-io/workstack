"""Tests for output formatting and progress indicators."""

import json
from unittest.mock import MagicMock

import pytest

from dot_agent_kit.data.kits.command.kit_cli_commands.command.output import (
    format_result,
    format_result_json,
    show_progress,
    show_tool_progress,
)


class TestShowToolProgress:
    """Tests for show_tool_progress function."""

    def test_show_tool_progress_known_tool(self, capsys: pytest.CaptureFixture) -> None:
        """Test progress indicator for known tool."""
        show_tool_progress("Bash")

        captured = capsys.readouterr()
        assert "🔨 Running command..." in captured.err

    def test_show_tool_progress_unknown_tool(self, capsys: pytest.CaptureFixture) -> None:
        """Test progress indicator for unknown tool."""
        show_tool_progress("UnknownTool")

        captured = capsys.readouterr()
        assert "⚙️  Executing UnknownTool..." in captured.err

    def test_show_tool_progress_all_known_tools(self, capsys: pytest.CaptureFixture) -> None:
        """Test that all known tools have indicators."""
        known_tools = [
            "Bash",
            "Task",
            "Read",
            "Write",
            "Edit",
            "Glob",
            "Grep",
            "Skill",
            "SlashCommand",
            "MultiEdit",
            "Delete",
            "Search",
            "WebFetch",
            "WebSearch",
        ]

        for tool in known_tools:
            show_tool_progress(tool)
            captured = capsys.readouterr()
            # Should have some indicator, not the default format
            assert captured.err.strip() != ""


class TestShowProgress:
    """Tests for show_progress function."""

    def test_show_progress_with_tool_blocks(self, capsys: pytest.CaptureFixture) -> None:
        """Test showing progress for tool use blocks."""
        # Create mock message with tool use block
        mock_tool_block = MagicMock()
        mock_tool_block.name = "Bash"

        mock_message = MagicMock()
        mock_message.content = [mock_tool_block]

        # Mock isinstance to return True for ToolUseBlock
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                "dot_agent_kit.data.kits.command.kit_cli_commands.command.output.ToolUseBlock",
                type(mock_tool_block),
            )

            show_progress(mock_message)

            captured = capsys.readouterr()
            assert "🔨 Running command..." in captured.err

    def test_show_progress_with_significant_text(self, capsys: pytest.CaptureFixture) -> None:
        """Test showing progress for significant text blocks."""
        mock_text_block = MagicMock()
        mock_text_block.text = "This is a significant piece of text that should be shown"

        mock_message = MagicMock()
        mock_message.content = [mock_text_block]

        # Mock isinstance to return True for TextBlock
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                "dot_agent_kit.data.kits.command.kit_cli_commands.command.output.TextBlock",
                type(mock_text_block),
            )

            show_progress(mock_message)

            captured = capsys.readouterr()
            assert "significant piece of text" in captured.err

    def test_show_progress_filters_short_text(self, capsys: pytest.CaptureFixture) -> None:
        """Test that short text blocks are filtered out."""
        mock_text_block = MagicMock()
        mock_text_block.text = "Short"

        mock_message = MagicMock()
        mock_message.content = [mock_text_block]

        # Mock isinstance to return True for TextBlock
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                "dot_agent_kit.data.kits.command.kit_cli_commands.command.output.TextBlock",
                type(mock_text_block),
            )

            show_progress(mock_message)

            captured = capsys.readouterr()
            # Short text should not be shown
            assert captured.err.strip() == ""


class TestFormatResult:
    """Tests for format_result function."""

    def test_format_result_success(self) -> None:
        """Test formatting successful result."""
        mock_result = MagicMock()
        mock_result.is_error = False
        mock_result.duration_ms = 1500
        mock_result.num_turns = 3
        mock_result.total_cost_usd = 0.0123

        result = format_result(mock_result)

        assert "✅ Command completed" in result
        assert "1500ms" in result
        assert "Turns: 3" in result
        assert "$0.0123" in result

    def test_format_result_error(self) -> None:
        """Test formatting error result."""
        mock_result = MagicMock()
        mock_result.is_error = True
        mock_result.duration_ms = 500
        mock_result.num_turns = 1
        mock_result.total_cost_usd = None

        result = format_result(mock_result)

        assert "❌ Command failed" in result
        assert "500ms" in result
        assert "Turns: 1" in result
        # Should not include cost when None
        assert "Cost:" not in result

    def test_format_result_no_cost(self) -> None:
        """Test formatting result without cost information."""
        mock_result = MagicMock()
        mock_result.is_error = False
        mock_result.duration_ms = 1000
        mock_result.num_turns = 2
        mock_result.total_cost_usd = None

        result = format_result(mock_result)

        assert "✅ Command completed" in result
        assert "Cost:" not in result


class TestFormatResultJson:
    """Tests for format_result_json function."""

    def test_format_result_json_complete(self) -> None:
        """Test JSON formatting with all fields."""
        mock_result = MagicMock()
        mock_result.is_error = False
        mock_result.duration_ms = 2000
        mock_result.num_turns = 4
        mock_result.total_cost_usd = 0.05
        mock_result.session_id = "session-123"

        additional_data = {"key": "value"}

        result = format_result_json(mock_result, additional_data)

        # Parse JSON to verify structure
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["duration_ms"] == 2000
        assert parsed["turns"] == 4
        assert parsed["cost_usd"] == 0.05
        assert parsed["session_id"] == "session-123"
        assert parsed["data"] == {"key": "value"}

    def test_format_result_json_error(self) -> None:
        """Test JSON formatting for error result."""
        mock_result = MagicMock()
        mock_result.is_error = True
        mock_result.duration_ms = 100
        mock_result.num_turns = 1
        mock_result.total_cost_usd = None
        mock_result.session_id = "session-456"

        result = format_result_json(mock_result, {})

        parsed = json.loads(result)
        assert parsed["success"] is False
        assert parsed["cost_usd"] is None
        assert parsed["data"] == {}
