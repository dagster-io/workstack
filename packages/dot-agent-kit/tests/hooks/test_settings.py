"""Tests for hooks settings operations."""

import json
import tempfile
from pathlib import Path

from dot_agent_kit.hooks.models import (
    ClaudeSettings,
    HookEntry,
    HookMetadata,
    MatcherGroup,
)
from dot_agent_kit.hooks.settings import (
    add_hook_to_settings,
    get_all_hooks,
    load_settings,
    merge_matcher_groups,
    remove_hooks_by_kit,
    save_settings,
)


class TestLoadSettings:
    """Tests for load_settings function."""

    def test_load_missing_file(self) -> None:
        """Test loading non-existent file returns empty settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "missing.json"
            settings = load_settings(path)
            assert settings.permissions is None
            assert settings.hooks is None

    def test_load_empty_json(self) -> None:
        """Test loading empty JSON object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            path.write_text("{}", encoding="utf-8")
            settings = load_settings(path)
            assert settings.permissions is None
            assert settings.hooks is None

    def test_load_with_hooks(self) -> None:
        """Test loading settings with hooks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            data = {
                "hooks": {
                    "user-prompt-submit": [
                        {
                            "matcher": "**",
                            "hooks": [
                                {
                                    "command": "python3 script.py",
                                    "timeout": 30,
                                    "_dot_agent": {
                                        "kit_id": "test-kit",
                                        "hook_id": "test-hook",
                                    },
                                }
                            ],
                        }
                    ]
                }
            }
            path.write_text(json.dumps(data), encoding="utf-8")
            settings = load_settings(path)
            assert settings.hooks is not None
            assert "user-prompt-submit" in settings.hooks


class TestSaveSettings:
    """Tests for save_settings function."""

    def test_save_empty_settings(self) -> None:
        """Test saving empty settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            settings = ClaudeSettings()
            save_settings(path, settings)
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            assert data == {}

    def test_creates_parent_directory(self) -> None:
        """Test that parent directory is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "dir" / "settings.json"
            settings = ClaudeSettings()
            save_settings(path, settings)
            assert path.exists()
            assert path.parent.exists()

    def test_preserves_extra_fields(self) -> None:
        """Test that extra fields are preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            # Create settings with extra fields
            original_data = {"permissions": {}, "custom_field": "value"}
            settings = ClaudeSettings.model_validate(original_data)
            save_settings(path, settings)

            # Load and verify
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            assert "custom_field" in data
            assert data["custom_field"] == "value"

    def test_adds_trailing_newline(self) -> None:
        """Test that file ends with newline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            settings = ClaudeSettings()
            save_settings(path, settings)
            content = path.read_text(encoding="utf-8")
            assert content.endswith("\n")


class TestAddHookToSettings:
    """Tests for add_hook_to_settings function."""

    def test_add_to_empty_settings(self) -> None:
        """Test adding hook to empty settings."""
        settings = ClaudeSettings()
        metadata = HookMetadata(kit_id="test-kit", hook_id="test-hook")
        entry = HookEntry(command="python3 script.py", timeout=30, _dot_agent=metadata)

        new_settings = add_hook_to_settings(settings, "user-prompt-submit", "**", entry)

        assert new_settings.hooks is not None
        assert "user-prompt-submit" in new_settings.hooks
        assert len(new_settings.hooks["user-prompt-submit"]) == 1
        assert new_settings.hooks["user-prompt-submit"][0].matcher == "**"

    def test_add_to_existing_matcher(self) -> None:
        """Test adding hook to existing matcher group."""
        metadata1 = HookMetadata(kit_id="kit1", hook_id="hook1")
        entry1 = HookEntry(command="python3 script1.py", timeout=30, _dot_agent=metadata1)
        group = MatcherGroup(matcher="**", hooks=[entry1])
        settings = ClaudeSettings(hooks={"user-prompt-submit": [group]})

        metadata2 = HookMetadata(kit_id="kit2", hook_id="hook2")
        entry2 = HookEntry(command="python3 script2.py", timeout=30, _dot_agent=metadata2)

        new_settings = add_hook_to_settings(settings, "user-prompt-submit", "**", entry2)

        assert new_settings.hooks is not None
        hooks = new_settings.hooks["user-prompt-submit"][0].hooks
        assert len(hooks) == 2

    def test_add_new_matcher_to_lifecycle(self) -> None:
        """Test adding hook with new matcher to existing lifecycle."""
        metadata1 = HookMetadata(kit_id="kit1", hook_id="hook1")
        entry1 = HookEntry(command="python3 script1.py", timeout=30, _dot_agent=metadata1)
        group = MatcherGroup(matcher="**", hooks=[entry1])
        settings = ClaudeSettings(hooks={"user-prompt-submit": [group]})

        metadata2 = HookMetadata(kit_id="kit2", hook_id="hook2")
        entry2 = HookEntry(command="python3 script2.py", timeout=30, _dot_agent=metadata2)

        new_settings = add_hook_to_settings(settings, "user-prompt-submit", "*.py", entry2)

        assert new_settings.hooks is not None
        assert len(new_settings.hooks["user-prompt-submit"]) == 2


class TestRemoveHooksByKit:
    """Tests for remove_hooks_by_kit function."""

    def test_remove_from_empty_settings(self) -> None:
        """Test removing from empty settings."""
        settings = ClaudeSettings()
        new_settings, count = remove_hooks_by_kit(settings, "test-kit")
        assert count == 0
        assert new_settings.hooks is None

    def test_remove_all_hooks_for_kit(self) -> None:
        """Test removing all hooks for a kit."""
        metadata = HookMetadata(kit_id="test-kit", hook_id="hook1")
        entry = HookEntry(command="python3 script.py", timeout=30, _dot_agent=metadata)
        group = MatcherGroup(matcher="**", hooks=[entry])
        settings = ClaudeSettings(hooks={"user-prompt-submit": [group]})

        new_settings, count = remove_hooks_by_kit(settings, "test-kit")

        assert count == 1
        assert new_settings.hooks is None  # All hooks removed

    def test_remove_partial_hooks(self) -> None:
        """Test removing some hooks but not all."""
        metadata1 = HookMetadata(kit_id="kit1", hook_id="hook1")
        entry1 = HookEntry(command="python3 script1.py", timeout=30, _dot_agent=metadata1)
        metadata2 = HookMetadata(kit_id="kit2", hook_id="hook2")
        entry2 = HookEntry(command="python3 script2.py", timeout=30, _dot_agent=metadata2)
        group = MatcherGroup(matcher="**", hooks=[entry1, entry2])
        settings = ClaudeSettings(hooks={"user-prompt-submit": [group]})

        new_settings, count = remove_hooks_by_kit(settings, "kit1")

        assert count == 1
        assert new_settings.hooks is not None
        assert len(new_settings.hooks["user-prompt-submit"][0].hooks) == 1


class TestGetAllHooks:
    """Tests for get_all_hooks function."""

    def test_get_from_empty_settings(self) -> None:
        """Test getting hooks from empty settings."""
        settings = ClaudeSettings()
        hooks = get_all_hooks(settings)
        assert hooks == []

    def test_get_all_hooks(self) -> None:
        """Test getting all hooks."""
        metadata = HookMetadata(kit_id="test-kit", hook_id="test-hook")
        entry = HookEntry(command="python3 script.py", timeout=30, _dot_agent=metadata)
        group = MatcherGroup(matcher="**", hooks=[entry])
        settings = ClaudeSettings(hooks={"user-prompt-submit": [group]})

        hooks = get_all_hooks(settings)

        assert len(hooks) == 1
        lifecycle, matcher, hook_entry = hooks[0]
        assert lifecycle == "user-prompt-submit"
        assert matcher == "**"
        assert hook_entry.command == "python3 script.py"


class TestMergeMatcherGroups:
    """Tests for merge_matcher_groups function."""

    def test_merge_empty_list(self) -> None:
        """Test merging empty list."""
        result = merge_matcher_groups([])
        assert result == []

    def test_merge_no_duplicates(self) -> None:
        """Test merging when no duplicates exist."""
        metadata = HookMetadata(kit_id="test-kit", hook_id="test-hook")
        entry = HookEntry(command="python3 script.py", timeout=30, _dot_agent=metadata)
        group1 = MatcherGroup(matcher="**", hooks=[entry])
        group2 = MatcherGroup(matcher="*.py", hooks=[entry])

        result = merge_matcher_groups([group1, group2])

        assert len(result) == 2

    def test_merge_duplicates(self) -> None:
        """Test merging duplicate matchers."""
        metadata1 = HookMetadata(kit_id="kit1", hook_id="hook1")
        entry1 = HookEntry(command="python3 script1.py", timeout=30, _dot_agent=metadata1)
        metadata2 = HookMetadata(kit_id="kit2", hook_id="hook2")
        entry2 = HookEntry(command="python3 script2.py", timeout=30, _dot_agent=metadata2)

        group1 = MatcherGroup(matcher="**", hooks=[entry1])
        group2 = MatcherGroup(matcher="**", hooks=[entry2])

        result = merge_matcher_groups([group1, group2])

        assert len(result) == 1
        assert len(result[0].hooks) == 2

    def test_preserves_order(self) -> None:
        """Test that first occurrence order is preserved."""
        metadata = HookMetadata(kit_id="test-kit", hook_id="test-hook")
        entry = HookEntry(command="python3 script.py", timeout=30, _dot_agent=metadata)
        group1 = MatcherGroup(matcher="*.py", hooks=[entry])
        group2 = MatcherGroup(matcher="**", hooks=[entry])
        group3 = MatcherGroup(matcher="*.py", hooks=[entry])

        result = merge_matcher_groups([group1, group2, group3])

        assert len(result) == 2
        assert result[0].matcher == "*.py"
        assert result[1].matcher == "**"
