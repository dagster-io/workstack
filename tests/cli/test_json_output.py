"""Tests for JSON output helpers.

These tests verify the JSON serialization, output routing, and error handling
for machine-parseable CLI output.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from erk.cli.json_output import (
    emit_json,
    emit_json_error,
    json_error_boundary,
)


def test_emit_json_with_dict_path_serialization() -> None:
    """Dict with Path objects should be serialized."""
    with patch("erk.cli.json_output.machine_output") as mock_machine_output:
        data = {"path": Path("/test"), "name": "test"}
        emit_json(data)

        mock_machine_output.assert_called_once()
        call_args = mock_machine_output.call_args[0][0]
        parsed = json.loads(call_args)
        assert parsed["path"] == "/test"
        assert parsed["name"] == "test"


def test_emit_json_with_dict_datetime_serialization() -> None:
    """Dict with datetime objects should be serialized."""
    with patch("erk.cli.json_output.machine_output") as mock_machine_output:
        dt = datetime(2025, 11, 17, 10, 30, 45, tzinfo=UTC)
        data = {"timestamp": dt, "name": "test"}
        emit_json(data)

        mock_machine_output.assert_called_once()
        call_args = mock_machine_output.call_args[0][0]
        parsed = json.loads(call_args)
        assert parsed["timestamp"] == "2025-11-17T10:30:45+00:00"
        assert parsed["name"] == "test"


def test_emit_json_with_nested_dict() -> None:
    """Nested dicts with special types should be recursively serialized."""
    with patch("erk.cli.json_output.machine_output") as mock_machine_output:
        data = {
            "metadata": {
                "path": Path("/test"),
                "timestamp": datetime(2025, 11, 17, tzinfo=UTC),
            },
            "name": "test",
        }
        emit_json(data)

        mock_machine_output.assert_called_once()
        call_args = mock_machine_output.call_args[0][0]
        parsed = json.loads(call_args)
        assert parsed["metadata"]["path"] == "/test"
        assert parsed["metadata"]["timestamp"] == "2025-11-17T00:00:00+00:00"
        assert parsed["name"] == "test"


@patch("erk.cli.json_output.machine_output")
def test_emit_json_routes_to_machine_output(mock_machine_output: MagicMock) -> None:
    """JSON output should be routed to machine_output (stdout)."""
    data = {"key": "value"}
    emit_json(data)

    mock_machine_output.assert_called_once()
    call_args = mock_machine_output.call_args[0][0]

    # Verify it's valid JSON
    parsed = json.loads(call_args)
    assert parsed == {"key": "value"}


@patch("erk.cli.json_output.machine_output")
def test_emit_json_formats_with_indent(mock_machine_output: MagicMock) -> None:
    """JSON output should be pretty-printed with 2-space indent."""
    data = {"key": "value", "nested": {"inner": "data"}}
    emit_json(data)

    call_args = mock_machine_output.call_args[0][0]
    # Check formatting - should have newlines and indentation
    assert "\n" in call_args
    assert "  " in call_args


# Test emit_json_error function


@patch("erk.cli.json_output.machine_output")
def test_emit_json_error_outputs_structured_error(mock_machine_output: MagicMock) -> None:
    """Error JSON should have error, error_type, and exit_code fields."""
    with pytest.raises(SystemExit) as exc_info:
        emit_json_error("Test error", "ValueError", exit_code=1)

    assert exc_info.value.code == 1

    call_args = mock_machine_output.call_args[0][0]
    parsed = json.loads(call_args)
    assert parsed == {
        "error": "Test error",
        "error_type": "ValueError",
        "exit_code": 1,
    }


@patch("erk.cli.json_output.machine_output")
def test_emit_json_error_custom_exit_code(mock_machine_output: MagicMock) -> None:
    """Error JSON should support custom exit codes."""
    with pytest.raises(SystemExit) as exc_info:
        emit_json_error("Test error", "CustomError", exit_code=42)

    assert exc_info.value.code == 42

    call_args = mock_machine_output.call_args[0][0]
    parsed = json.loads(call_args)
    assert parsed["exit_code"] == 42


@patch("erk.cli.json_output.machine_output")
def test_emit_json_error_default_exit_code(mock_machine_output: MagicMock) -> None:
    """Error JSON should default to exit code 1."""
    with pytest.raises(SystemExit) as exc_info:
        emit_json_error("Test error", "ValueError")

    assert exc_info.value.code == 1


# Test json_error_boundary decorator


def test_json_error_boundary_text_mode_reraises() -> None:
    """In text mode, exceptions should bubble up normally."""

    @json_error_boundary
    def failing_command(format: str) -> None:
        raise ValueError("Test error")

    with pytest.raises(ValueError, match="Test error"):
        failing_command(format="text")


@patch("erk.cli.json_output.machine_output")
def test_json_error_boundary_json_mode_emits_json(mock_machine_output: MagicMock) -> None:
    """In JSON mode, exceptions should be caught and output as JSON."""

    @json_error_boundary
    def failing_command(format: str) -> None:
        raise ValueError("Test error")

    with pytest.raises(SystemExit) as exc_info:
        failing_command(format="json")

    assert exc_info.value.code == 1

    call_args = mock_machine_output.call_args[0][0]
    parsed = json.loads(call_args)
    assert parsed["error"] == "Test error"
    assert parsed["error_type"] == "ValueError"
    assert parsed["exit_code"] == 1


def test_json_error_boundary_passes_through_system_exit() -> None:
    """SystemExit should pass through without modification."""

    @json_error_boundary
    def command_with_exit(format: str) -> None:
        raise SystemExit(42)

    with pytest.raises(SystemExit) as exc_info:
        command_with_exit(format="text")

    assert exc_info.value.code == 42

    with pytest.raises(SystemExit) as exc_info:
        command_with_exit(format="json")

    assert exc_info.value.code == 42


def test_json_error_boundary_default_format_text() -> None:
    """When format parameter is missing, should behave like text mode."""

    @json_error_boundary
    def command_without_format() -> None:
        raise ValueError("Test error")

    with pytest.raises(ValueError, match="Test error"):
        command_without_format()


def test_json_error_boundary_preserves_function_metadata() -> None:
    """Decorator should preserve function name and docstring."""

    @json_error_boundary
    def my_command(format: str) -> None:
        """Test command docstring."""
        pass

    assert my_command.__name__ == "my_command"
    assert my_command.__doc__ == "Test command docstring."


def test_json_error_boundary_success_returns_value() -> None:
    """Successful execution should return the function's return value."""

    @json_error_boundary
    def successful_command(format: str) -> str:
        return "success"

    result = successful_command(format="text")
    assert result == "success"

    result = successful_command(format="json")
    assert result == "success"


@patch("erk.cli.json_output.machine_output")
def test_json_error_boundary_with_kwargs(mock_machine_output: MagicMock) -> None:
    """Decorator should work with commands that use **kwargs."""

    @json_error_boundary
    def command_with_kwargs(**kwargs: str) -> None:
        raise ValueError("Test error")

    with pytest.raises(SystemExit):
        command_with_kwargs(format="json", other="value")

    call_args = mock_machine_output.call_args[0][0]
    parsed = json.loads(call_args)
    assert parsed["error"] == "Test error"


@patch("erk.cli.json_output.machine_output")
def test_json_error_boundary_extracts_error_type(mock_machine_output: MagicMock) -> None:
    """Decorator should correctly extract error type from exception class."""

    class CustomError(Exception):
        pass

    @json_error_boundary
    def failing_command(format: str) -> None:
        raise CustomError("Custom error message")

    with pytest.raises(SystemExit):
        failing_command(format="json")

    call_args = mock_machine_output.call_args[0][0]
    parsed = json.loads(call_args)
    assert parsed["error_type"] == "CustomError"
