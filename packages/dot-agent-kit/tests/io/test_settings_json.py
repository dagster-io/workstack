"""Tests for settings.json I/O operations."""

import json
from pathlib import Path

from dot_agent_kit.io.settings_json import (
    get_hooks_dir,
    get_settings_path,
    load_settings,
    save_settings,
)
from dot_agent_kit.models.settings import ClaudeSettings, MatcherGroup


def test_load_settings_nonexistent_file(tmp_path: Path) -> None:
    """Test loading settings when file doesn't exist returns empty settings."""
    settings_path = tmp_path / "settings.json"

    settings = load_settings(settings_path)

    assert settings.hooks == {}
    assert settings.other == {}


def test_load_settings_empty_file(tmp_path: Path) -> None:
    """Test loading settings from empty JSON file."""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{}", encoding="utf-8")

    settings = load_settings(settings_path)

    assert settings.hooks == {}
    assert settings.other == {}


def test_load_settings_with_hooks(tmp_path: Path) -> None:
    """Test loading settings with hooks."""
    settings_path = tmp_path / "settings.json"
    data = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {"type": "command", "command": "test", "timeout": 30},
                    ],
                }
            ]
        }
    }
    settings_path.write_text(json.dumps(data), encoding="utf-8")

    settings = load_settings(settings_path)

    assert "PreToolUse" in settings.hooks
    assert len(settings.hooks["PreToolUse"]) == 1
    assert settings.hooks["PreToolUse"][0].matcher == "Bash"


def test_save_settings_creates_directory(tmp_path: Path) -> None:
    """Test save_settings creates parent directories if needed."""
    settings_path = tmp_path / "subdir" / "settings.json"
    settings = ClaudeSettings.empty()

    save_settings(settings_path, settings)

    assert settings_path.exists()
    assert settings_path.parent.exists()


def test_save_settings_atomic_write(tmp_path: Path) -> None:
    """Test save_settings uses atomic write with temp file."""
    settings_path = tmp_path / "settings.json"
    settings = ClaudeSettings(
        hooks={"PreToolUse": [MatcherGroup(matcher="Bash", hooks=[])]},
    )

    save_settings(settings_path, settings)

    assert settings_path.exists()
    assert not (tmp_path / "settings.json.tmp").exists()

    content = settings_path.read_text(encoding="utf-8")
    data = json.loads(content)
    assert "hooks" in data


def test_save_settings_formatting(tmp_path: Path) -> None:
    """Test save_settings produces properly formatted JSON."""
    settings_path = tmp_path / "settings.json"
    settings = ClaudeSettings.model_validate(
        {
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": []}]},
            "key": "value",
        }
    )

    save_settings(settings_path, settings)

    content = settings_path.read_text(encoding="utf-8")

    assert content.endswith("\n")
    data = json.loads(content)
    assert isinstance(data, dict)


def test_save_load_roundtrip(tmp_path: Path) -> None:
    """Test save and load roundtrip preserves data."""
    settings_path = tmp_path / "settings.json"
    # Use model_validate to properly set extra fields
    original = ClaudeSettings.model_validate(
        {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [{"type": "command", "command": "test", "timeout": 30}],
                    }
                ]
            },
            "custom": "value",  # Extra field will be preserved by Pydantic
        }
    )

    save_settings(settings_path, original)
    loaded = load_settings(settings_path)

    assert len(loaded.hooks) == 1
    assert "PreToolUse" in loaded.hooks
    assert loaded.hooks["PreToolUse"][0].matcher == "Bash"
    assert loaded.other["custom"] == "value"


def test_get_settings_path() -> None:
    """Test get_settings_path returns project-level path."""
    path = get_settings_path()

    assert path == Path.cwd() / ".claude" / "settings.json"


def test_get_hooks_dir() -> None:
    """Test get_hooks_dir returns project-level path."""
    path = get_hooks_dir("my-kit")

    assert path == Path.cwd() / ".claude" / "hooks" / "my-kit"
