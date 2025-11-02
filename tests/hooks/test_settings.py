"""Tests for settings.json I/O and hook manipulation operations."""

import json
from pathlib import Path

from dot_agent_kit.hooks.models import ClaudeSettings, HookEntry, HookMetadata, MatcherGroup
from dot_agent_kit.hooks.settings import (
    InstalledHook,
    add_hook_to_settings,
    get_all_hooks,
    load_settings,
    merge_matcher_groups,
    remove_hooks_by_kit,
    save_settings,
)


# Helper factories for test data
def create_hook_entry(
    kit_id: str = "test-kit",
    hook_id: str = "test-hook",
    command: str = "echo test",
    timeout: int = 30,
) -> HookEntry:
    """Factory function for creating test HookEntry objects."""
    return HookEntry(
        command=command,
        timeout=timeout,
        dot_agent=HookMetadata(kit_id=kit_id, hook_id=hook_id),
    )


def create_matcher_group(
    matcher: str = "**",
    hooks: list[HookEntry] | None = None,
) -> MatcherGroup:
    """Factory function for creating test MatcherGroup objects."""
    if hooks is None:
        hooks = [create_hook_entry()]
    return MatcherGroup(matcher=matcher, hooks=hooks)


def create_settings(
    hooks: dict[str, list[MatcherGroup]] | None = None,
    permissions: dict[str, list[str]] | None = None,
    extra_fields: dict[str, str] | None = None,
) -> ClaudeSettings:
    """Factory function for creating test ClaudeSettings objects."""
    # Extra fields are passed as kwargs to the constructor
    extra = extra_fields if extra_fields else {}
    return ClaudeSettings(
        hooks=hooks,
        permissions=permissions,
        **extra,
    )


class TestLoadSettings:
    """Tests for load_settings function."""

    def test_load_settings_nonexistent_file_returns_empty(self, tmp_path: Path) -> None:
        """Test that loading nonexistent file returns empty ClaudeSettings."""
        nonexistent = tmp_path / "nonexistent.json"

        result = load_settings(nonexistent)

        assert isinstance(result, ClaudeSettings)
        assert result.hooks is None
        assert result.permissions is None

    def test_load_settings_valid_json(self, tmp_path: Path) -> None:
        """Test loading valid settings.json file."""
        settings_file = tmp_path / "settings.json"
        settings_data = {
            "hooks": {
                "user-prompt-submit": [
                    {
                        "matcher": "**",
                        "hooks": [
                            {
                                "command": "echo test",
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
        settings_file.write_text(json.dumps(settings_data), encoding="utf-8")

        result = load_settings(settings_file)

        assert result.hooks is not None
        assert "user-prompt-submit" in result.hooks
        assert len(result.hooks["user-prompt-submit"]) == 1
        assert result.hooks["user-prompt-submit"][0].matcher == "**"

    def test_load_settings_preserves_extra_fields(self, tmp_path: Path) -> None:
        """Test that unknown fields are preserved (backward compatibility)."""
        settings_file = tmp_path / "settings.json"
        settings_data = {
            "hooks": {},
            "customField": "customValue",
            "anotherField": 123,
        }
        settings_file.write_text(json.dumps(settings_data), encoding="utf-8")

        result = load_settings(settings_file)

        assert result.model_extra is not None
        assert result.model_extra["customField"] == "customValue"
        assert result.model_extra["anotherField"] == 123

    def test_load_settings_empty_json(self, tmp_path: Path) -> None:
        """Test loading empty JSON object."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{}", encoding="utf-8")

        result = load_settings(settings_file)

        assert isinstance(result, ClaudeSettings)
        assert result.hooks is None
        assert result.permissions is None


class TestSaveSettings:
    """Tests for save_settings function."""

    def test_save_settings_creates_parent_directory(self, tmp_path: Path) -> None:
        """Test that parent directory is created if it doesn't exist."""
        nested_path = tmp_path / "nested" / "dir" / "settings.json"
        settings = create_settings()

        save_settings(nested_path, settings)

        assert nested_path.exists()
        assert nested_path.parent.exists()

    def test_save_settings_writes_valid_json(self, tmp_path: Path) -> None:
        """Test that settings are written as valid JSON."""
        settings_file = tmp_path / "settings.json"
        hook_entry = create_hook_entry()
        matcher_group = create_matcher_group(hooks=[hook_entry])
        settings = create_settings(hooks={"user-prompt-submit": [matcher_group]})

        save_settings(settings_file, settings)

        assert settings_file.exists()
        content = settings_file.read_text(encoding="utf-8")
        data = json.loads(content)
        assert "hooks" in data
        assert "user-prompt-submit" in data["hooks"]

    def test_save_settings_excludes_none_fields(self, tmp_path: Path) -> None:
        """Test that None fields are excluded from output."""
        settings_file = tmp_path / "settings.json"
        settings = create_settings(hooks=None, permissions=None)

        save_settings(settings_file, settings)

        content = settings_file.read_text(encoding="utf-8")
        data = json.loads(content)
        assert "hooks" not in data
        assert "permissions" not in data

    def test_save_settings_uses_field_aliases(self, tmp_path: Path) -> None:
        """Test that field aliases are used in output (_dot_agent)."""
        settings_file = tmp_path / "settings.json"
        hook_entry = create_hook_entry()
        matcher_group = create_matcher_group(hooks=[hook_entry])
        settings = create_settings(hooks={"user-prompt-submit": [matcher_group]})

        save_settings(settings_file, settings)

        content = settings_file.read_text(encoding="utf-8")
        data = json.loads(content)
        hook_data = data["hooks"]["user-prompt-submit"][0]["hooks"][0]
        assert "_dot_agent" in hook_data
        assert "dot_agent" not in hook_data

    def test_save_settings_round_trip_preserves_data(self, tmp_path: Path) -> None:
        """Test that save → load cycle preserves all data."""
        settings_file = tmp_path / "settings.json"
        hook1 = create_hook_entry(kit_id="kit1", hook_id="hook1")
        hook2 = create_hook_entry(kit_id="kit2", hook_id="hook2")
        matcher_group = create_matcher_group(matcher="**/*.py", hooks=[hook1, hook2])
        original_settings = create_settings(
            hooks={"user-prompt-submit": [matcher_group]},
            permissions={"allow": ["git:*"]},
        )

        save_settings(settings_file, original_settings)
        loaded_settings = load_settings(settings_file)

        assert loaded_settings.hooks is not None
        assert "user-prompt-submit" in loaded_settings.hooks
        assert len(loaded_settings.hooks["user-prompt-submit"]) == 1
        assert loaded_settings.hooks["user-prompt-submit"][0].matcher == "**/*.py"
        assert len(loaded_settings.hooks["user-prompt-submit"][0].hooks) == 2
        assert loaded_settings.permissions == {"allow": ["git:*"]}

    def test_save_settings_adds_trailing_newline(self, tmp_path: Path) -> None:
        """Test that saved file has trailing newline."""
        settings_file = tmp_path / "settings.json"
        settings = create_settings()

        save_settings(settings_file, settings)

        content = settings_file.read_text(encoding="utf-8")
        assert content.endswith("\n")


class TestAddHookToSettings:
    """Tests for add_hook_to_settings function."""

    def test_add_hook_to_settings_empty_settings(self) -> None:
        """Test adding hook to empty settings creates structure."""
        settings = create_settings()
        entry = create_hook_entry()

        result = add_hook_to_settings(settings, "user-prompt-submit", "**", entry)

        assert result.hooks is not None
        assert "user-prompt-submit" in result.hooks
        assert len(result.hooks["user-prompt-submit"]) == 1
        assert result.hooks["user-prompt-submit"][0].matcher == "**"
        assert len(result.hooks["user-prompt-submit"][0].hooks) == 1

    def test_add_hook_to_settings_creates_new_matcher_group(self) -> None:
        """Test adding hook with new matcher creates new group."""
        existing_entry = create_hook_entry(kit_id="existing")
        existing_group = create_matcher_group(matcher="**/*.py", hooks=[existing_entry])
        settings = create_settings(hooks={"user-prompt-submit": [existing_group]})
        new_entry = create_hook_entry(kit_id="new")

        result = add_hook_to_settings(settings, "user-prompt-submit", "**/*.ts", new_entry)

        assert result.hooks is not None
        assert len(result.hooks["user-prompt-submit"]) == 2
        matchers = [g.matcher for g in result.hooks["user-prompt-submit"]]
        assert "**/*.py" in matchers
        assert "**/*.ts" in matchers

    def test_add_hook_to_settings_appends_to_existing_matcher_group(self) -> None:
        """Test adding hook to existing matcher group appends to list."""
        existing_entry = create_hook_entry(kit_id="existing")
        existing_group = create_matcher_group(matcher="**", hooks=[existing_entry])
        settings = create_settings(hooks={"user-prompt-submit": [existing_group]})
        new_entry = create_hook_entry(kit_id="new")

        result = add_hook_to_settings(settings, "user-prompt-submit", "**", new_entry)

        assert result.hooks is not None
        assert len(result.hooks["user-prompt-submit"]) == 1
        assert len(result.hooks["user-prompt-submit"][0].hooks) == 2

    def test_add_hook_to_settings_immutability(self) -> None:
        """Test that original settings object is not modified."""
        entry = create_hook_entry()
        settings = create_settings()
        original_hooks = settings.hooks

        result = add_hook_to_settings(settings, "user-prompt-submit", "**", entry)

        assert settings.hooks is original_hooks  # Original unchanged
        assert result is not settings  # New object returned
        assert result.hooks is not None  # Result has hooks

    def test_add_hook_to_settings_preserves_extra_fields(self) -> None:
        """Test that extra fields are preserved in new settings."""
        settings = create_settings(extra_fields={"customField": "value"})
        entry = create_hook_entry()

        result = add_hook_to_settings(settings, "user-prompt-submit", "**", entry)

        assert result.model_extra is not None
        assert result.model_extra["customField"] == "value"

    def test_add_hook_to_settings_creates_new_lifecycle(self) -> None:
        """Test adding hook to new lifecycle key."""
        existing_entry = create_hook_entry()
        existing_group = create_matcher_group(hooks=[existing_entry])
        settings = create_settings(hooks={"user-prompt-submit": [existing_group]})
        new_entry = create_hook_entry(kit_id="new")

        result = add_hook_to_settings(settings, "tool-result", "**", new_entry)

        assert result.hooks is not None
        assert "user-prompt-submit" in result.hooks
        assert "tool-result" in result.hooks
        assert len(result.hooks["tool-result"]) == 1


class TestRemoveHooksByKit:
    """Tests for remove_hooks_by_kit function."""

    def test_remove_hooks_by_kit_removes_matching_hooks(self) -> None:
        """Test that hooks with matching kit_id are removed."""
        hook1 = create_hook_entry(kit_id="remove-me", hook_id="hook1")
        hook2 = create_hook_entry(kit_id="keep-me", hook_id="hook2")
        hook3 = create_hook_entry(kit_id="remove-me", hook_id="hook3")
        group = create_matcher_group(hooks=[hook1, hook2, hook3])
        settings = create_settings(hooks={"user-prompt-submit": [group]})

        result, count = remove_hooks_by_kit(settings, "remove-me")

        assert count == 2
        assert result.hooks is not None
        remaining_hooks = result.hooks["user-prompt-submit"][0].hooks
        assert len(remaining_hooks) == 1
        assert remaining_hooks[0].dot_agent.kit_id == "keep-me"

    def test_remove_hooks_by_kit_cleans_up_empty_matcher_groups(self) -> None:
        """Test that empty matcher groups are removed."""
        hook1 = create_hook_entry(kit_id="remove-me")
        hook2 = create_hook_entry(kit_id="keep-me")
        group1 = create_matcher_group(matcher="**/*.py", hooks=[hook1])
        group2 = create_matcher_group(matcher="**/*.ts", hooks=[hook2])
        settings = create_settings(hooks={"user-prompt-submit": [group1, group2]})

        result, count = remove_hooks_by_kit(settings, "remove-me")

        assert count == 1
        assert result.hooks is not None
        assert len(result.hooks["user-prompt-submit"]) == 1
        assert result.hooks["user-prompt-submit"][0].matcher == "**/*.ts"

    def test_remove_hooks_by_kit_cleans_up_empty_lifecycle_entries(self) -> None:
        """Test that empty lifecycle entries are removed."""
        hook = create_hook_entry(kit_id="remove-me")
        group = create_matcher_group(hooks=[hook])
        settings = create_settings(hooks={"user-prompt-submit": [group]})

        result, count = remove_hooks_by_kit(settings, "remove-me")

        assert count == 1
        # Hooks should be None or empty since all were removed
        assert result.hooks is None or len(result.hooks) == 0

    def test_remove_hooks_by_kit_returns_zero_for_no_matches(self) -> None:
        """Test that zero is returned when no hooks match."""
        hook = create_hook_entry(kit_id="keep-me")
        group = create_matcher_group(hooks=[hook])
        settings = create_settings(hooks={"user-prompt-submit": [group]})

        result, count = remove_hooks_by_kit(settings, "nonexistent-kit")

        assert count == 0
        assert result.hooks is not None
        assert len(result.hooks["user-prompt-submit"][0].hooks) == 1

    def test_remove_hooks_by_kit_empty_settings(self) -> None:
        """Test removing from empty settings returns unchanged."""
        settings = create_settings()

        result, count = remove_hooks_by_kit(settings, "any-kit")

        assert count == 0
        assert result.hooks is None

    def test_remove_hooks_by_kit_immutability(self) -> None:
        """Test that original settings object is not modified."""
        hook = create_hook_entry(kit_id="remove-me")
        group = create_matcher_group(hooks=[hook])
        settings = create_settings(hooks={"user-prompt-submit": [group]})
        original_hooks = settings.hooks

        result, count = remove_hooks_by_kit(settings, "remove-me")

        assert settings.hooks is original_hooks  # Original unchanged
        assert result is not settings  # New object returned

    def test_remove_hooks_by_kit_preserves_other_lifecycles(self) -> None:
        """Test that hooks in other lifecycles are preserved."""
        hook1 = create_hook_entry(kit_id="remove-me")
        hook2 = create_hook_entry(kit_id="keep-me")
        group1 = create_matcher_group(hooks=[hook1])
        group2 = create_matcher_group(hooks=[hook2])
        settings = create_settings(hooks={"user-prompt-submit": [group1], "tool-result": [group2]})

        result, count = remove_hooks_by_kit(settings, "remove-me")

        assert count == 1
        assert result.hooks is not None
        assert "tool-result" in result.hooks
        assert len(result.hooks["tool-result"]) == 1


class TestGetAllHooks:
    """Tests for get_all_hooks function."""

    def test_get_all_hooks_empty_settings(self) -> None:
        """Test that empty settings returns empty list."""
        settings = create_settings()

        result = get_all_hooks(settings)

        assert result == []

    def test_get_all_hooks_extracts_with_context(self) -> None:
        """Test that hooks are extracted with lifecycle and matcher context."""
        hook = create_hook_entry(kit_id="test-kit", hook_id="test-hook")
        group = create_matcher_group(matcher="**/*.py", hooks=[hook])
        settings = create_settings(hooks={"user-prompt-submit": [group]})

        result = get_all_hooks(settings)

        assert len(result) == 1
        assert isinstance(result[0], InstalledHook)
        assert result[0].lifecycle == "user-prompt-submit"
        assert result[0].matcher == "**/*.py"
        assert result[0].entry.dot_agent.kit_id == "test-kit"

    def test_get_all_hooks_multiple_lifecycles_and_matchers(self) -> None:
        """Test extraction from multiple lifecycles and matcher groups."""
        hook1 = create_hook_entry(kit_id="kit1", hook_id="hook1")
        hook2 = create_hook_entry(kit_id="kit2", hook_id="hook2")
        hook3 = create_hook_entry(kit_id="kit3", hook_id="hook3")

        group1 = create_matcher_group(matcher="**/*.py", hooks=[hook1])
        group2 = create_matcher_group(matcher="**/*.ts", hooks=[hook2])
        group3 = create_matcher_group(matcher="**", hooks=[hook3])

        settings = create_settings(
            hooks={
                "user-prompt-submit": [group1, group2],
                "tool-result": [group3],
            }
        )

        result = get_all_hooks(settings)

        assert len(result) == 3
        lifecycles = {h.lifecycle for h in result}
        assert lifecycles == {"user-prompt-submit", "tool-result"}
        matchers = {h.matcher for h in result}
        assert matchers == {"**/*.py", "**/*.ts", "**"}

    def test_get_all_hooks_multiple_hooks_in_group(self) -> None:
        """Test extraction when matcher group has multiple hooks."""
        hook1 = create_hook_entry(kit_id="kit1")
        hook2 = create_hook_entry(kit_id="kit2")
        hook3 = create_hook_entry(kit_id="kit3")
        group = create_matcher_group(hooks=[hook1, hook2, hook3])
        settings = create_settings(hooks={"user-prompt-submit": [group]})

        result = get_all_hooks(settings)

        assert len(result) == 3
        kit_ids = {h.entry.dot_agent.kit_id for h in result}
        assert kit_ids == {"kit1", "kit2", "kit3"}


class TestMergeMatcherGroups:
    """Tests for merge_matcher_groups function."""

    def test_merge_matcher_groups_empty_list(self) -> None:
        """Test that empty list returns empty list."""
        result = merge_matcher_groups([])

        assert result == []

    def test_merge_matcher_groups_single_group_unchanged(self) -> None:
        """Test that single group is returned unchanged."""
        group = create_matcher_group(matcher="**/*.py")

        result = merge_matcher_groups([group])

        assert len(result) == 1
        assert result[0].matcher == "**/*.py"

    def test_merge_matcher_groups_merges_duplicates(self) -> None:
        """Test that duplicate matchers are merged."""
        hook1 = create_hook_entry(kit_id="kit1")
        hook2 = create_hook_entry(kit_id="kit2")
        hook3 = create_hook_entry(kit_id="kit3")

        group1 = create_matcher_group(matcher="**", hooks=[hook1])
        group2 = create_matcher_group(matcher="**/*.py", hooks=[hook2])
        group3 = create_matcher_group(matcher="**", hooks=[hook3])

        result = merge_matcher_groups([group1, group2, group3])

        assert len(result) == 2
        merged_group = next(g for g in result if g.matcher == "**")
        assert len(merged_group.hooks) == 2  # hook1 and hook3

    def test_merge_matcher_groups_preserves_order(self) -> None:
        """Test that order of first occurrence is preserved."""
        hook1 = create_hook_entry(kit_id="kit1")
        hook2 = create_hook_entry(kit_id="kit2")
        hook3 = create_hook_entry(kit_id="kit3")

        group1 = create_matcher_group(matcher="**/*.ts", hooks=[hook1])
        group2 = create_matcher_group(matcher="**/*.py", hooks=[hook2])
        group3 = create_matcher_group(matcher="**/*.ts", hooks=[hook3])

        result = merge_matcher_groups([group1, group2, group3])

        assert len(result) == 2
        assert result[0].matcher == "**/*.ts"  # First occurrence
        assert result[1].matcher == "**/*.py"

    def test_merge_matcher_groups_combines_all_hooks(self) -> None:
        """Test that all hooks from matching groups are combined."""
        hook1 = create_hook_entry(kit_id="kit1")
        hook2 = create_hook_entry(kit_id="kit2")
        hook3 = create_hook_entry(kit_id="kit3")
        hook4 = create_hook_entry(kit_id="kit4")

        group1 = create_matcher_group(matcher="**", hooks=[hook1, hook2])
        group2 = create_matcher_group(matcher="**", hooks=[hook3])
        group3 = create_matcher_group(matcher="**", hooks=[hook4])

        result = merge_matcher_groups([group1, group2, group3])

        assert len(result) == 1
        assert len(result[0].hooks) == 4

    def test_merge_matcher_groups_no_duplicates(self) -> None:
        """Test that groups with unique matchers are all preserved."""
        group1 = create_matcher_group(matcher="**/*.py")
        group2 = create_matcher_group(matcher="**/*.ts")
        group3 = create_matcher_group(matcher="**/*.js")

        result = merge_matcher_groups([group1, group2, group3])

        assert len(result) == 3
        matchers = {g.matcher for g in result}
        assert matchers == {"**/*.py", "**/*.ts", "**/*.js"}
