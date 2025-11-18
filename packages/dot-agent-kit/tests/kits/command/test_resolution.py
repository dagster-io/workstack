"""Tests for command resolution logic."""

from pathlib import Path

import pytest

from dot_agent_kit.data.kits.command.kit_cli_commands.command.models import (
    CommandNotFoundError,
)
from dot_agent_kit.data.kits.command.kit_cli_commands.command.resolution import (
    read_command_markdown,
    resolve_command_file,
)


class TestResolveCommandFile:
    """Tests for resolve_command_file function."""

    def test_resolve_top_level_command(self, tmp_path: Path) -> None:
        """Test resolving a top-level command."""
        # Setup
        commands_dir = tmp_path / ".claude" / "commands"
        commands_dir.mkdir(parents=True)
        command_file = commands_dir / "ensure-ci.md"
        command_file.write_text("# CI Check\nRun all CI checks", encoding="utf-8")

        # Execute
        result = resolve_command_file("ensure-ci", tmp_path)

        # Verify
        assert result == command_file
        assert result.exists()

    def test_resolve_namespaced_command(self, tmp_path: Path) -> None:
        """Test resolving a namespaced command."""
        # Setup
        commands_dir = tmp_path / ".claude" / "commands" / "gt"
        commands_dir.mkdir(parents=True)
        command_file = commands_dir / "submit-branch.md"
        command_file.write_text("# Submit Branch\nSubmit PR", encoding="utf-8")

        # Execute
        result = resolve_command_file("gt:submit-branch", tmp_path)

        # Verify
        assert result == command_file
        assert result.exists()

    def test_missing_commands_directory(self, tmp_path: Path) -> None:
        """Test error when .claude/commands directory missing."""
        # Execute and verify
        with pytest.raises(CommandNotFoundError, match="No .claude/commands directory found"):
            resolve_command_file("ensure-ci", tmp_path)

    def test_missing_command_file(self, tmp_path: Path) -> None:
        """Test error when command file doesn't exist."""
        # Setup
        commands_dir = tmp_path / ".claude" / "commands"
        commands_dir.mkdir(parents=True)

        # Execute and verify
        with pytest.raises(CommandNotFoundError, match="Command not found: missing"):
            resolve_command_file("missing", tmp_path)

    def test_missing_namespaced_command(self, tmp_path: Path) -> None:
        """Test error when namespaced command file doesn't exist."""
        # Setup
        commands_dir = tmp_path / ".claude" / "commands" / "gt"
        commands_dir.mkdir(parents=True)

        # Execute and verify
        with pytest.raises(CommandNotFoundError, match="Command not found: gt:missing"):
            resolve_command_file("gt:missing", tmp_path)

    def test_multiple_colons_in_name(self, tmp_path: Path) -> None:
        """Test handling command names with multiple colons."""
        # Setup
        commands_dir = tmp_path / ".claude" / "commands" / "foo"
        commands_dir.mkdir(parents=True)
        command_file = commands_dir / "bar:baz.md"
        command_file.write_text("# Test\nContent", encoding="utf-8")

        # Execute
        result = resolve_command_file("foo:bar:baz", tmp_path)

        # Verify - splits on first colon only
        assert result == command_file


class TestReadCommandMarkdown:
    """Tests for read_command_markdown function."""

    def test_read_command_content(self, tmp_path: Path) -> None:
        """Test reading command markdown file."""
        # Setup
        command_file = tmp_path / "command.md"
        expected_content = "# Test Command\n\nThis is the command prompt."
        command_file.write_text(expected_content, encoding="utf-8")

        # Execute
        result = read_command_markdown(command_file)

        # Verify
        assert result == expected_content

    def test_read_empty_file(self, tmp_path: Path) -> None:
        """Test reading empty command file."""
        # Setup
        command_file = tmp_path / "empty.md"
        command_file.write_text("", encoding="utf-8")

        # Execute
        result = read_command_markdown(command_file)

        # Verify
        assert result == ""
