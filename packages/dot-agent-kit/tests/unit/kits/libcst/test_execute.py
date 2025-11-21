"""Tests for libcst execute command."""

import json
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from dot_agent_kit.data.kits.libcst.kit_cli_commands.libcst.execute import execute


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


class TestExecuteCommand:
    """Tests for the execute command."""

    def test_execute_requires_files_argument(self, runner: CliRunner) -> None:
        """Test that --files argument is required."""
        result = runner.invoke(execute, [])

        assert result.exit_code != 0
        assert "Missing option '--files'" in result.output or "Error" in result.output

    def test_execute_with_no_code_provided(self, runner: CliRunner) -> None:
        """Test that command fails when no code provided via stdin or --code."""
        result = runner.invoke(execute, ["--files", "*.py"])

        assert result.exit_code == 1
        output_data = json.loads(result.output)
        assert output_data["success"] is False
        assert "No transformation code provided" in output_data["errors"][0]

    def test_execute_with_empty_code(self, runner: CliRunner) -> None:
        """Test that command fails when code is empty."""
        result = runner.invoke(execute, ["--code", "   ", "--files", "*.py"])

        assert result.exit_code == 1
        output_data = json.loads(result.output)
        assert output_data["success"] is False
        assert "empty" in output_data["errors"][0].lower()

    @patch("dot_agent_kit.data.kits.libcst.kit_cli_commands.libcst.execute.subprocess.run")
    def test_execute_with_valid_code(self, mock_subprocess: Mock, runner: CliRunner) -> None:
        """Test successful execution with valid transformation code."""
        # Mock subprocess to return success JSON
        mock_result = Mock()
        mock_result.stdout = json.dumps(
            {"success": True, "files_modified": ["test.py"], "changes_count": 5, "errors": []}
        )
        mock_subprocess.return_value = mock_result

        simple_code = """
import json
import sys
result = {"success": True, "files_modified": [], "changes_count": 0, "errors": []}
print(json.dumps(result))
"""

        result = runner.invoke(execute, ["--code", simple_code, "--files", "*.py"])

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data["success"] is True

    @patch("dot_agent_kit.data.kits.libcst.kit_cli_commands.libcst.execute.subprocess.run")
    def test_execute_with_dry_run(self, mock_subprocess: Mock, runner: CliRunner) -> None:
        """Test that --dry-run flag sets DRY_RUN environment variable."""
        mock_result = Mock()
        mock_result.stdout = json.dumps(
            {"success": True, "files_modified": [], "changes_count": 0, "errors": []}
        )
        mock_subprocess.return_value = mock_result

        simple_code = "print('test')"

        runner.invoke(execute, ["--code", simple_code, "--files", "*.py", "--dry-run"])

        # Verify subprocess was called with DRY_RUN in environment
        assert mock_subprocess.called
        call_kwargs = mock_subprocess.call_args[1]
        assert "env" in call_kwargs
        assert call_kwargs["env"].get("DRY_RUN") == "1"

    @patch("dot_agent_kit.data.kits.libcst.kit_cli_commands.libcst.execute.subprocess.run")
    def test_execute_handles_subprocess_error(
        self, mock_subprocess: Mock, runner: CliRunner
    ) -> None:
        """Test error handling when subprocess fails."""
        from subprocess import CalledProcessError

        mock_subprocess.side_effect = CalledProcessError(
            returncode=1, cmd=["python", "script.py"], stderr="Transformation failed: syntax error"
        )

        simple_code = "invalid python code {"

        runner.invoke(execute, ["--code", simple_code, "--files", "*.py"])

        # Verify subprocess was called (it will fail with error)
        assert mock_subprocess.called
