"""Tests for hooks data models."""

import pytest
from pydantic import ValidationError

from dot_agent_kit.hooks.models import (
    ClaudeSettings,
    HookDefinition,
    HookEntry,
    HookMetadata,
    MatcherGroup,
)


class TestHookMetadata:
    """Tests for HookMetadata model."""

    def test_create_valid_metadata(self) -> None:
        """Test creating valid metadata."""
        metadata = HookMetadata(kit_id="test-kit", hook_id="test-hook")
        assert metadata.kit_id == "test-kit"
        assert metadata.hook_id == "test-hook"

    def test_immutability(self) -> None:
        """Test that metadata is immutable."""
        metadata = HookMetadata(kit_id="test-kit", hook_id="test-hook")
        with pytest.raises((AttributeError, ValidationError)):
            metadata.kit_id = "new-kit"  # type: ignore

    def test_rejects_empty_kit_id(self) -> None:
        """Test that empty kit_id is rejected."""
        with pytest.raises(ValidationError):
            HookMetadata(kit_id="", hook_id="test-hook")

    def test_rejects_empty_hook_id(self) -> None:
        """Test that empty hook_id is rejected."""
        with pytest.raises(ValidationError):
            HookMetadata(kit_id="test-kit", hook_id="")


class TestHookEntry:
    """Tests for HookEntry model."""

    def test_create_valid_entry(self) -> None:
        """Test creating valid hook entry."""
        metadata = HookMetadata(kit_id="test-kit", hook_id="test-hook")
        entry = HookEntry(
            command='python3 "/path/to/script.py"',
            timeout=30,
            _dot_agent=metadata,
        )
        assert entry.command == 'python3 "/path/to/script.py"'
        assert entry.timeout == 30
        assert entry.dot_agent.kit_id == "test-kit"

    def test_aliased_field_parsing(self) -> None:
        """Test that _dot_agent alias works in parsing."""
        data = {
            "command": 'python3 "/path/to/script.py"',
            "timeout": 30,
            "_dot_agent": {"kit_id": "test-kit", "hook_id": "test-hook"},
        }
        entry = HookEntry.model_validate(data)
        assert entry.dot_agent.kit_id == "test-kit"

    def test_immutability(self) -> None:
        """Test that entry is immutable."""
        metadata = HookMetadata(kit_id="test-kit", hook_id="test-hook")
        entry = HookEntry(command="python3 script.py", timeout=30, _dot_agent=metadata)
        with pytest.raises((AttributeError, ValidationError)):
            entry.command = "new command"  # type: ignore

    def test_rejects_negative_timeout(self) -> None:
        """Test that negative timeout is rejected."""
        metadata = HookMetadata(kit_id="test-kit", hook_id="test-hook")
        with pytest.raises(ValidationError):
            HookEntry(command="python3 script.py", timeout=-1, _dot_agent=metadata)

    def test_rejects_zero_timeout(self) -> None:
        """Test that zero timeout is rejected."""
        metadata = HookMetadata(kit_id="test-kit", hook_id="test-hook")
        with pytest.raises(ValidationError):
            HookEntry(command="python3 script.py", timeout=0, _dot_agent=metadata)


class TestMatcherGroup:
    """Tests for MatcherGroup model."""

    def test_create_valid_group(self) -> None:
        """Test creating valid matcher group."""
        metadata = HookMetadata(kit_id="test-kit", hook_id="test-hook")
        entry = HookEntry(command="python3 script.py", timeout=30, _dot_agent=metadata)
        group = MatcherGroup(matcher="**", hooks=[entry])
        assert group.matcher == "**"
        assert len(group.hooks) == 1

    def test_empty_hooks_list(self) -> None:
        """Test group with empty hooks list."""
        group = MatcherGroup(matcher="**", hooks=[])
        assert group.matcher == "**"
        assert len(group.hooks) == 0

    def test_immutability(self) -> None:
        """Test that group is immutable."""
        group = MatcherGroup(matcher="**", hooks=[])
        with pytest.raises((AttributeError, ValidationError)):
            group.matcher = "*.py"  # type: ignore


class TestClaudeSettings:
    """Tests for ClaudeSettings model."""

    def test_create_empty_settings(self) -> None:
        """Test creating empty settings."""
        settings = ClaudeSettings()
        assert settings.permissions is None
        assert settings.hooks is None

    def test_create_with_hooks(self) -> None:
        """Test creating settings with hooks."""
        metadata = HookMetadata(kit_id="test-kit", hook_id="test-hook")
        entry = HookEntry(command="python3 script.py", timeout=30, _dot_agent=metadata)
        group = MatcherGroup(matcher="**", hooks=[entry])
        settings = ClaudeSettings(hooks={"UserPromptSubmit": [group]})
        assert settings.hooks is not None
        assert "UserPromptSubmit" in settings.hooks

    def test_preserves_unknown_fields(self) -> None:
        """Test that unknown fields are preserved."""
        data = {
            "permissions": {"allow": ["git:*"]},
            "hooks": {},
            "unknown_field": "value",
            "another_field": 123,
        }
        settings = ClaudeSettings.model_validate(data)
        assert settings.model_extra is not None
        assert "unknown_field" in settings.model_extra
        assert settings.model_extra["unknown_field"] == "value"
        assert settings.model_extra["another_field"] == 123


class TestHookDefinition:
    """Tests for HookDefinition model."""

    def test_create_valid_definition(self) -> None:
        """Test creating valid hook definition."""
        hook = HookDefinition(
            id="test-hook",
            lifecycle="UserPromptSubmit",
            matcher="**",
            script="hooks/test.py",
            description="Test hook",
            timeout=30,
        )
        assert hook.id == "test-hook"
        assert hook.lifecycle == "UserPromptSubmit"
        assert hook.timeout == 30

    def test_default_timeout(self) -> None:
        """Test default timeout value."""
        hook = HookDefinition(
            id="test-hook",
            lifecycle="UserPromptSubmit",
            matcher="**",
            script="hooks/test.py",
            description="Test hook",
        )
        assert hook.timeout == 30

    def test_immutability(self) -> None:
        """Test that definition is immutable."""
        hook = HookDefinition(
            id="test-hook",
            lifecycle="UserPromptSubmit",
            matcher="**",
            script="hooks/test.py",
            description="Test hook",
        )
        with pytest.raises((AttributeError, ValidationError)):
            hook.id = "new-id"  # type: ignore

    def test_rejects_whitespace_only_lifecycle(self) -> None:
        """Test that whitespace-only lifecycle is rejected."""
        with pytest.raises(ValidationError):
            HookDefinition(
                id="test-hook",
                lifecycle="   ",
                matcher="**",
                script="hooks/test.py",
                description="Test hook",
            )

    def test_optional_matcher(self) -> None:
        """Test that matcher can be omitted."""
        hook = HookDefinition(
            id="test-hook",
            lifecycle="UserPromptSubmit",
            script="hooks/test.py",
            description="Test hook",
        )
        assert hook.matcher is None

    def test_explicit_none_matcher(self) -> None:
        """Test that matcher can be explicitly set to None."""
        hook = HookDefinition(
            id="test-hook",
            lifecycle="UserPromptSubmit",
            matcher=None,
            script="hooks/test.py",
            description="Test hook",
        )
        assert hook.matcher is None

    def test_rejects_whitespace_only_script(self) -> None:
        """Test that whitespace-only script is rejected."""
        with pytest.raises(ValidationError):
            HookDefinition(
                id="test-hook",
                lifecycle="UserPromptSubmit",
                matcher="**",
                script="   ",
                description="Test hook",
            )

    def test_rejects_whitespace_only_description(self) -> None:
        """Test that whitespace-only description is rejected."""
        with pytest.raises(ValidationError):
            HookDefinition(
                id="test-hook",
                lifecycle="UserPromptSubmit",
                matcher="**",
                script="hooks/test.py",
                description="   ",
            )

    def test_rejects_negative_timeout(self) -> None:
        """Test that negative timeout is rejected."""
        with pytest.raises(ValidationError):
            HookDefinition(
                id="test-hook",
                lifecycle="UserPromptSubmit",
                matcher="**",
                script="hooks/test.py",
                description="Test hook",
                timeout=-1,
            )

    def test_rejects_zero_timeout(self) -> None:
        """Test that zero timeout is rejected."""
        with pytest.raises(ValidationError):
            HookDefinition(
                id="test-hook",
                lifecycle="UserPromptSubmit",
                matcher="**",
                script="hooks/test.py",
                description="Test hook",
                timeout=0,
            )
