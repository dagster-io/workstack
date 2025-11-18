"""Command resolution logic."""

from pathlib import Path

from dot_agent_kit.data.kits.command.kit_cli_commands.command.models import (
    CommandNotFoundError,
)


def resolve_command_file(command_name: str, cwd: Path) -> Path:
    """Resolve command name to .claude/commands/ file path.

    Examples:
        gt:submit-branch → .claude/commands/gt/submit-branch.md
        ensure-ci → .claude/commands/ensure-ci.md

    Raises:
        CommandNotFoundError: If command file doesn't exist
    """
    commands_dir = cwd / ".claude" / "commands"

    # Check .claude/commands exists
    if not commands_dir.exists():
        raise CommandNotFoundError(f"No .claude/commands directory found in {cwd}")

    # Parse namespace
    if ":" in command_name:
        namespace, name = command_name.split(":", 1)
        command_path = commands_dir / namespace / f"{name}.md"
    else:
        command_path = commands_dir / f"{command_name}.md"

    # Check file exists
    if not command_path.exists():
        raise CommandNotFoundError(f"Command not found: {command_name}\nExpected: {command_path}")

    return command_path


def read_command_markdown(path: Path) -> str:
    """Read command markdown file and extract content."""
    return path.read_text(encoding="utf-8")
