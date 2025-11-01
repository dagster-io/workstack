"""Tests for hook removal operations."""

from pathlib import Path

from dot_agent_kit.io.settings_json import load_settings, save_settings
from dot_agent_kit.models.settings import ClaudeSettings, MatcherGroup
from dot_agent_kit.operations.hook_removal import (
    remove_hook_by_id,
    remove_hooks,
    remove_hooks_by_kit_id,
)


def test_remove_hooks_by_kit_id() -> None:
    """Test removing hooks by kit_id."""
    bash_hook = {
        "type": "command",
        "command": "test1",
        "_dot_agent": {"kit_id": "kit-a", "hook_id": "hook1", "enabled": True, "priority": 10},
    }
    write_hook = {
        "type": "command",
        "command": "test2",
        "_dot_agent": {"kit_id": "kit-b", "hook_id": "hook2", "enabled": True, "priority": 20},
    }

    settings = ClaudeSettings(
        hooks={
            "PreToolUse": [
                MatcherGroup(matcher="Bash", hooks=[bash_hook, write_hook]),
            ]
        },
    )

    result = remove_hooks_by_kit_id(settings, "kit-a")

    assert len(result.hooks["PreToolUse"][0].hooks) == 1
    remaining_hook = result.hooks["PreToolUse"][0].hooks[0]
    assert remaining_hook["_dot_agent"]["kit_id"] == "kit-b"  # type: ignore[index]


def test_remove_hooks_by_kit_id_all_hooks() -> None:
    """Test removing all hooks for a kit removes the group."""
    hook1 = {
        "type": "command",
        "command": "test1",
        "_dot_agent": {"kit_id": "kit-a", "hook_id": "hook1", "enabled": True, "priority": 10},
    }
    hook2 = {
        "type": "command",
        "command": "test2",
        "_dot_agent": {"kit_id": "kit-a", "hook_id": "hook2", "enabled": True, "priority": 20},
    }

    settings = ClaudeSettings(
        hooks={
            "PreToolUse": [
                MatcherGroup(matcher="Bash", hooks=[hook1, hook2]),
            ]
        },
    )

    result = remove_hooks_by_kit_id(settings, "kit-a")

    assert "PreToolUse" not in result.hooks


def test_remove_hook_by_id_specific() -> None:
    """Test removing a specific hook by kit_id and hook_id."""
    hook1 = {
        "type": "command",
        "command": "test1",
        "_dot_agent": {"kit_id": "kit-a", "hook_id": "hook1", "enabled": True, "priority": 10},
    }
    hook2 = {
        "type": "command",
        "command": "test2",
        "_dot_agent": {"kit_id": "kit-a", "hook_id": "hook2", "enabled": True, "priority": 20},
    }

    settings = ClaudeSettings(
        hooks={
            "PreToolUse": [
                MatcherGroup(matcher="Bash", hooks=[hook1, hook2]),
            ]
        },
    )

    result = remove_hook_by_id(settings, "kit-a", "hook1")

    assert len(result.hooks["PreToolUse"][0].hooks) == 1
    remaining_hook = result.hooks["PreToolUse"][0].hooks[0]
    assert remaining_hook["_dot_agent"]["hook_id"] == "hook2"  # type: ignore[index]


def test_remove_hook_by_id_wrong_kit() -> None:
    """Test remove_hook_by_id with wrong kit_id doesn't remove hook."""
    hook = {
        "type": "command",
        "command": "test",
        "_dot_agent": {"kit_id": "kit-a", "hook_id": "hook1", "enabled": True, "priority": 10},
    }

    settings = ClaudeSettings(
        hooks={
            "PreToolUse": [
                MatcherGroup(matcher="Bash", hooks=[hook]),
            ]
        },
    )

    result = remove_hook_by_id(settings, "kit-b", "hook1")

    assert len(result.hooks["PreToolUse"][0].hooks) == 1


def test_remove_hooks_integration(tmp_path: Path) -> None:
    """Test full hook removal including file cleanup."""
    claude_dir = tmp_path / ".claude"
    settings_path = claude_dir / "settings.json"
    hooks_dir = claude_dir / "hooks" / "my-kit"

    hooks_dir.mkdir(parents=True)
    (hooks_dir / "validator.py").write_text("# hook", encoding="utf-8")

    hook = {
        "type": "command",
        "command": "test",
        "_dot_agent": {"kit_id": "my-kit", "hook_id": "validator", "enabled": True, "priority": 10},
    }

    settings = ClaudeSettings(
        hooks={
            "PreToolUse": [
                MatcherGroup(matcher="Bash", hooks=[hook]),
            ]
        },
    )
    save_settings(settings_path, settings)

    def mock_get_settings_path() -> Path:
        return settings_path

    def mock_get_hooks_dir(kit_name: str) -> Path:
        return claude_dir / "hooks" / kit_name

    import dot_agent_kit.operations.hook_removal as hook_removal_module

    original_get_settings = hook_removal_module.get_settings_path
    original_get_hooks = hook_removal_module.get_hooks_dir

    try:
        hook_removal_module.get_settings_path = mock_get_settings_path
        hook_removal_module.get_hooks_dir = mock_get_hooks_dir

        removed_ids = remove_hooks("my-kit")

        assert "validator" in removed_ids

        assert not hooks_dir.exists()

        loaded_settings = load_settings(settings_path)
        assert loaded_settings.hooks == {}

    finally:
        hook_removal_module.get_settings_path = original_get_settings
        hook_removal_module.get_hooks_dir = original_get_hooks


def test_remove_hooks_partial_removal(tmp_path: Path) -> None:
    """Test removing hooks from one kit preserves others."""
    claude_dir = tmp_path / ".claude"
    settings_path = claude_dir / "settings.json"

    hook1 = {
        "type": "command",
        "command": "test1",
        "_dot_agent": {"kit_id": "kit-a", "hook_id": "hook1", "enabled": True, "priority": 10},
    }
    hook2 = {
        "type": "command",
        "command": "test2",
        "_dot_agent": {"kit_id": "kit-b", "hook_id": "hook2", "enabled": True, "priority": 20},
    }

    settings = ClaudeSettings(
        hooks={
            "PreToolUse": [
                MatcherGroup(matcher="Bash", hooks=[hook1, hook2]),
            ]
        },
    )
    save_settings(settings_path, settings)

    (claude_dir / "hooks" / "kit-a").mkdir(parents=True)

    def mock_get_settings_path() -> Path:
        return settings_path

    def mock_get_hooks_dir(kit_name: str) -> Path:
        return claude_dir / "hooks" / kit_name

    import dot_agent_kit.operations.hook_removal as hook_removal_module

    original_get_settings = hook_removal_module.get_settings_path
    original_get_hooks = hook_removal_module.get_hooks_dir

    try:
        hook_removal_module.get_settings_path = mock_get_settings_path
        hook_removal_module.get_hooks_dir = mock_get_hooks_dir

        removed_ids = remove_hooks("kit-a")

        assert "hook1" in removed_ids

        loaded_settings = load_settings(settings_path)
        assert len(loaded_settings.hooks["PreToolUse"][0].hooks) == 1
        remaining = loaded_settings.hooks["PreToolUse"][0].hooks[0]
        assert remaining["_dot_agent"]["kit_id"] == "kit-b"  # type: ignore[index]

    finally:
        hook_removal_module.get_settings_path = original_get_settings
        hook_removal_module.get_hooks_dir = original_get_hooks


def test_remove_hooks_preserves_hooks_without_metadata() -> None:
    """Test removal preserves hooks without _dot_agent metadata."""
    hook_with_metadata: dict[str, object] = {
        "type": "command",
        "command": "test1",
        "_dot_agent": {"kit_id": "kit-a", "hook_id": "hook1", "enabled": True, "priority": 10},
    }
    hook_without_metadata: dict[str, object] = {
        "type": "command",
        "command": "test2",
    }

    settings = ClaudeSettings(
        hooks={
            "PreToolUse": [
                MatcherGroup(matcher="Bash", hooks=[hook_with_metadata, hook_without_metadata]),
            ]
        },
    )

    result = remove_hooks_by_kit_id(settings, "kit-a")

    assert len(result.hooks["PreToolUse"][0].hooks) == 1
    assert result.hooks["PreToolUse"][0].hooks[0] == hook_without_metadata
