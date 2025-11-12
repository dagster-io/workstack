"""Tests for local-standards-reminder-hook CLI command."""

import importlib.util
from pathlib import Path

from click.testing import CliRunner


# Load the command module dynamically since the directory name contains hyphens
_MODULE_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "src"
    / "dot_agent_kit"
    / "data"
    / "kits"
    / "workstack-local-standards"
    / "kit_cli_commands"
    / "workstack-local-standards"
    / "local_standards_reminder_hook.py"
)

spec = importlib.util.spec_from_file_location("local_standards_reminder_hook", _MODULE_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Cannot load module from {_MODULE_PATH}")

_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_module)
local_standards_reminder_hook = _module.local_standards_reminder_hook


class TestLocalStandardsReminderHook:
    """Tests for the local-standards-reminder-hook command."""

    def test_command_executes_successfully(self, cli_runner: CliRunner) -> None:
        """Test that the command executes without errors."""
        result = cli_runner.invoke(local_standards_reminder_hook)

        assert result.exit_code == 0

    def test_output_has_reminder_tags(self, cli_runner: CliRunner) -> None:
        """Test that output is wrapped in <reminder> tags."""
        result = cli_runner.invoke(local_standards_reminder_hook)

        assert result.exit_code == 0
        assert "<reminder>" in result.output
        assert "</reminder>" in result.output

    def test_output_has_header(self, cli_runner: CliRunner) -> None:
        """Test that output includes the main header."""
        result = cli_runner.invoke(local_standards_reminder_hook)

        assert result.exit_code == 0
        assert "🟡 WORKSTACK LOCAL STANDARDS" in result.output
        assert "workstack-local-standards skill" in result.output

    def test_output_has_all_key_conventions(self, cli_runner: CliRunner) -> None:
        """Test that all key conventions are mentioned in output."""
        result = cli_runner.invoke(local_standards_reminder_hook)

        assert result.exit_code == 0

        # Verify all 6 key conventions are present
        expected_conventions = [
            ".claude/ artifacts: kebab-case",
            "Ops abstractions",
            "Context regeneration",
            "CLI tools: Use runner agent",
            "Graphite stacks: upstack=away from main, downstack=toward main",
            "Test isolation",
        ]

        for convention in expected_conventions:
            assert convention in result.output, f"Missing convention: {convention}"

    def test_output_formatting(self, cli_runner: CliRunner) -> None:
        """Test that output has proper formatting with bullet points."""
        result = cli_runner.invoke(local_standards_reminder_hook)

        assert result.exit_code == 0
        assert "Key conventions:" in result.output
        # Check for bullet points
        assert "  •" in result.output

    def test_unicode_characters_render(self, cli_runner: CliRunner) -> None:
        """Test that unicode emoji and bullet points render correctly."""
        result = cli_runner.invoke(local_standards_reminder_hook)

        assert result.exit_code == 0
        # Verify emoji is present
        assert "🟡" in result.output
        # Verify bullet points are present
        assert "•" in result.output

    def test_mentions_hardcoded_paths_warning(self, cli_runner: CliRunner) -> None:
        """Test that the critical hardcoded paths warning is mentioned."""
        result = cli_runner.invoke(local_standards_reminder_hook)

        assert result.exit_code == 0
        assert "NEVER hardcoded paths" in result.output or "hardcoded paths" in result.output.lower()

    def test_mentions_subprocess_warning(self, cli_runner: CliRunner) -> None:
        """Test that subprocess usage warning is mentioned."""
        result = cli_runner.invoke(local_standards_reminder_hook)

        assert result.exit_code == 0
        assert "not subprocess" in result.output

    def test_output_structure(self, cli_runner: CliRunner) -> None:
        """Test the overall structure of the output."""
        result = cli_runner.invoke(local_standards_reminder_hook)

        assert result.exit_code == 0

        output_lines = result.output.split("\n")

        # Should have multiple lines
        assert len(output_lines) > 5

        # First line should be opening tag
        assert output_lines[0] == "<reminder>"

        # Last non-empty line should be closing tag
        non_empty_lines = [line for line in output_lines if line.strip()]
        assert non_empty_lines[-1] == "</reminder>"
