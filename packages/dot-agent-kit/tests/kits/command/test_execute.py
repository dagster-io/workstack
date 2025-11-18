"""Tests for command execution CLI."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from dot_agent_kit.data.kits.command.kit_cli_commands.command.execute import execute


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


class TestExecuteCommand:
    """Tests for execute CLI command."""

    def test_execute_missing_api_key(self, runner: CliRunner) -> None:
        """Test execution fails when API key is missing."""
        with runner.isolated_filesystem():
            # Setup command directory structure inside isolated filesystem
            commands_dir = Path(".claude") / "commands"
            commands_dir.mkdir(parents=True)
            command_file = commands_dir / "test-command.md"
            command_file.write_text("# Test\nTest", encoding="utf-8")

            # Run without API key environment variable
            result = runner.invoke(execute, ["test-command"], env={"ANTHROPIC_API_KEY": ""})

            assert result.exit_code == 1
            assert "ANTHROPIC_API_KEY not set" in result.output

    def test_execute_command_not_found(self, runner: CliRunner) -> None:
        """Test execution fails when command file not found."""
        with runner.isolated_filesystem():
            # Setup command directory but no command file
            commands_dir = Path(".claude") / "commands"
            commands_dir.mkdir(parents=True)

            result = runner.invoke(execute, ["missing-command", "--api-key", "test-key"])

            assert result.exit_code == 1
            assert "Command not found" in result.output

    def test_execute_success(self, runner: CliRunner) -> None:
        """Test successful command execution."""
        # Mock the async execution
        mock_result_message = MagicMock()
        mock_result_message.is_error = False
        mock_result_message.duration_ms = 1000
        mock_result_message.num_turns = 2
        mock_result_message.total_cost_usd = 0.01

        with runner.isolated_filesystem():
            # Setup command file inside isolated filesystem
            commands_dir = Path(".claude") / "commands"
            commands_dir.mkdir(parents=True)
            command_file = commands_dir / "test.md"
            command_file.write_text("# Test Command\nTest prompt", encoding="utf-8")
            with patch(
                "dot_agent_kit.data.kits.command.kit_cli_commands.command.execute.anyio.run"
            ) as mock_anyio_run:
                mock_command_result = MagicMock()
                mock_command_result.sdk_result = mock_result_message
                mock_command_result.data = {}
                mock_anyio_run.return_value = mock_command_result

                result = runner.invoke(execute, ["test", "--api-key", "test-key"])

                assert result.exit_code == 0
                assert "✅ Command completed" in result.output

    def test_execute_error(self, runner: CliRunner) -> None:
        """Test command execution with error."""
        # Mock the async execution with error
        mock_result_message = MagicMock()
        mock_result_message.is_error = True
        mock_result_message.duration_ms = 500
        mock_result_message.num_turns = 1
        mock_result_message.total_cost_usd = None

        with runner.isolated_filesystem():
            # Setup command file inside isolated filesystem
            commands_dir = Path(".claude") / "commands"
            commands_dir.mkdir(parents=True)
            command_file = commands_dir / "error-test.md"
            command_file.write_text("# Error Test\nTest prompt", encoding="utf-8")
            with patch(
                "dot_agent_kit.data.kits.command.kit_cli_commands.command.execute.anyio.run"
            ) as mock_anyio_run:
                mock_command_result = MagicMock()
                mock_command_result.sdk_result = mock_result_message
                mock_command_result.data = {}
                mock_anyio_run.return_value = mock_command_result

                result = runner.invoke(execute, ["error-test", "--api-key", "test-key"])

                assert result.exit_code == 1
                assert "❌ Command failed" in result.output

    def test_execute_json_output(self, runner: CliRunner) -> None:
        """Test command execution with JSON output."""
        # Mock the async execution
        mock_result_message = MagicMock()
        mock_result_message.is_error = False
        mock_result_message.duration_ms = 800
        mock_result_message.num_turns = 1
        mock_result_message.total_cost_usd = 0.005
        mock_result_message.session_id = "session-123"

        with runner.isolated_filesystem():
            # Setup command file inside isolated filesystem
            commands_dir = Path(".claude") / "commands"
            commands_dir.mkdir(parents=True)
            command_file = commands_dir / "json-test.md"
            command_file.write_text("# JSON Test\nTest prompt", encoding="utf-8")
            with patch(
                "dot_agent_kit.data.kits.command.kit_cli_commands.command.execute.anyio.run"
            ) as mock_anyio_run:
                mock_command_result = MagicMock()
                mock_command_result.sdk_result = mock_result_message
                mock_command_result.data = {"key": "value"}
                mock_anyio_run.return_value = mock_command_result

                result = runner.invoke(execute, ["json-test", "--api-key", "test-key", "--json"])

                assert result.exit_code == 0
                # Output should be JSON
                import json

                output_data = json.loads(result.output)
                assert output_data["success"] is True
                assert output_data["duration_ms"] == 800
                assert output_data["data"] == {"key": "value"}

    def test_execute_unexpected_error(self, runner: CliRunner) -> None:
        """Test handling of unexpected errors."""
        with runner.isolated_filesystem():
            # Setup command file inside isolated filesystem
            commands_dir = Path(".claude") / "commands"
            commands_dir.mkdir(parents=True)
            command_file = commands_dir / "crash-test.md"
            command_file.write_text("# Crash Test\nTest prompt", encoding="utf-8")
            with patch(
                "dot_agent_kit.data.kits.command.kit_cli_commands.command.execute.anyio.run"
            ) as mock_anyio_run:
                mock_anyio_run.side_effect = RuntimeError("Unexpected error")

                result = runner.invoke(execute, ["crash-test", "--api-key", "test-key"])

                assert result.exit_code == 1
                assert "Unexpected error" in result.output


# Note: Integration tests for execute_command_async would require pytest-asyncio
# and would make real API calls with the SDK. These are intentionally omitted
# from unit tests to keep tests fast and avoid API costs.
