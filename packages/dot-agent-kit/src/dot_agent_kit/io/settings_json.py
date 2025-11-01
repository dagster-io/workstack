"""I/O operations for Claude Code settings.json files.

This module provides safe read/write operations for settings.json with
atomic writes.
"""

import json
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path

from dot_agent_kit.models.settings import ClaudeSettings


def load_settings(settings_path: Path) -> ClaudeSettings:
    """Load settings.json from disk.

    Args:
        settings_path: Path to settings.json file

    Returns:
        ClaudeSettings object, or empty settings if file doesn't exist
    """
    if not settings_path.exists():
        return ClaudeSettings.empty()

    json_str = settings_path.read_text(encoding="utf-8")
    return ClaudeSettings.model_validate_json(json_str)


def save_settings(settings_path: Path, settings: ClaudeSettings) -> None:
    """Save settings.json to disk atomically.

    Writes to a temporary file first, then renames to avoid corruption.
    Creates parent directories if they don't exist.

    Args:
        settings_path: Path to settings.json file
        settings: Settings object to save
    """
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = settings_path.with_suffix(".json.tmp")

    # Get JSON string with sorted keys for consistent formatting
    json_str = settings.model_dump_json(indent=2)

    # Parse and re-dump with sort_keys=True for consistent key ordering
    data = json.loads(json_str)
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")

    temp_path.replace(settings_path)


def get_settings_path() -> Path:
    """Get settings.json path for the current project.

    Returns:
        Path to ./.claude/settings.json
    """
    return Path.cwd() / ".claude" / "settings.json"


def get_hooks_dir(kit_name: str) -> Path:
    """Get directory for hook scripts.

    Args:
        kit_name: Name of the kit

    Returns:
        Path to hooks directory for the kit in ./.claude/hooks/
    """
    return Path.cwd() / ".claude" / "hooks" / kit_name


@contextmanager
def modify_settings(
    settings_path: Path,
) -> Generator[tuple[ClaudeSettings, Callable[[ClaudeSettings], None]]]:
    """Context manager for modifying settings.

    This provides atomic read-modify-write access to settings.json.

    Args:
        settings_path: Path to settings.json file

    Yields:
        Tuple of (current_settings, save_function)

    Example:
        with modify_settings(path) as (settings, save):
            new_settings = update_hooks(settings)
            save(new_settings)
    """
    settings = load_settings(settings_path)

    def save_fn(new_settings: ClaudeSettings) -> None:
        save_settings(settings_path, new_settings)

    yield settings, save_fn
