"""Tests for CLI functionality."""

from click.testing import CliRunner

from dot_agent_kit import __version__
from dot_agent_kit.cli import cli


def test_cli_invocation(cli_runner: CliRunner) -> None:
    """Test CLI loads without error."""
    result = cli_runner.invoke(cli)
    assert result.exit_code == 0


def test_version_flag(cli_runner: CliRunner) -> None:
    """Test --version displays correct version."""
    result = cli_runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_help_text(cli_runner: CliRunner) -> None:
    """Test help text is displayed."""
    result = cli_runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Manage Claude Code kits" in result.output
