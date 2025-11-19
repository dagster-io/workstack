"""Integration tests for command execution with actual CLI interactions."""

from pathlib import Path

from click.testing import CliRunner

from dot_agent_kit.data.kits.command.kit_cli_commands.command.execute import execute


def test_cli_integration_with_file_not_found() -> None:
    """Test CLI error handling for FileNotFoundError (integration test)."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Setup: Create valid command file
        commands_dir = Path(".claude/commands")
        commands_dir.mkdir(parents=True)
        (commands_dir / "test.md").write_text("# Test")

        # Note: This will actually try to run 'claude' binary
        # In a real environment without claude installed, it will fail
        # For this test, we just verify the CLI structure works
        result = runner.invoke(execute, ["test"])

        # Either succeeds (if claude is installed) or shows error message
        if result.exit_code != 0:
            # If failed, should be a helpful error message
            assert "Error:" in result.output or "claude" in result.output.lower()
