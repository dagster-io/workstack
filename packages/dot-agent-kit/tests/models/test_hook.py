"""Tests for hook models."""

import pytest
from pydantic import ValidationError

from dot_agent_kit.models.hook import HookDefinition, HookEntry, HookMetadata


def test_hook_definition_defaults() -> None:
    """Test HookDefinition with default values."""
    hook = HookDefinition(
        hook_id="validator",
        lifecycle="PreToolUse",
        matcher="Bash",
        script="hooks/validator.py",
        description="Validate commands",
    )

    assert hook.hook_id == "validator"
    assert hook.lifecycle == "PreToolUse"
    assert hook.matcher == "Bash"
    assert hook.script == "hooks/validator.py"
    assert hook.description == "Validate commands"
    assert hook.timeout == 30


def test_hook_definition_custom_values() -> None:
    """Test HookDefinition with custom values."""
    hook = HookDefinition(
        hook_id="formatter",
        lifecycle="PostToolUse",
        matcher="Write|Edit",
        script="hooks/formatter.py",
        description="Format files",
        timeout=60,
    )

    assert hook.timeout == 60


def test_hook_metadata() -> None:
    """Test HookMetadata creation."""
    metadata = HookMetadata(
        kit_id="my-kit",
        hook_id="validator",
    )

    assert metadata.kit_id == "my-kit"
    assert metadata.hook_id == "validator"


def test_hook_entry_to_dict() -> None:
    """Test HookEntry conversion to dict."""
    metadata = HookMetadata(
        kit_id="my-kit",
        hook_id="validator",
    )

    entry = HookEntry(
        type="command",
        command='python3 "/path/to/validator.py"',
        timeout=30,
        **{"_dot_agent": metadata},  # Use alias via unpacking
    )

    result = entry.model_dump()

    assert result["type"] == "command"
    assert result["command"] == 'python3 "/path/to/validator.py"'
    assert result["timeout"] == 30
    assert "_dot_agent" in result

    dot_agent = result["_dot_agent"]
    if not isinstance(dot_agent, dict):
        msg = "_dot_agent should be a dict"
        raise AssertionError(msg)

    assert dot_agent["kit_id"] == "my-kit"
    assert dot_agent["hook_id"] == "validator"


def test_hook_entry_from_dict() -> None:
    """Test HookEntry parsing from dict."""
    data = {
        "type": "command",
        "command": 'python3 "/path/to/validator.py"',
        "timeout": 30,
        "_dot_agent": {
            "kit_id": "my-kit",
            "hook_id": "validator",
        },
    }

    entry = HookEntry.model_validate(data)

    assert entry.type == "command"
    assert entry.command == 'python3 "/path/to/validator.py"'
    assert entry.timeout == 30
    assert entry.metadata.kit_id == "my-kit"
    assert entry.metadata.hook_id == "validator"


def test_hook_entry_from_dict_missing_metadata() -> None:
    """Test HookEntry.from_dict with missing _dot_agent field."""
    data = {
        "type": "command",
        "command": 'python3 "/path/to/validator.py"',
        "timeout": 30,
    }

    with pytest.raises(ValidationError):
        HookEntry.model_validate(data)


def test_hook_entry_from_dict_invalid_metadata_type() -> None:
    """Test HookEntry.from_dict with invalid metadata type."""
    data = {
        "type": "command",
        "command": 'python3 "/path/to/validator.py"',
        "timeout": 30,
        "_dot_agent": "not a dict",
    }

    with pytest.raises(ValidationError):
        HookEntry.model_validate(data)


def test_hook_entry_from_dict_invalid_field_types() -> None:
    """Test HookEntry.from_dict with invalid field types."""
    with pytest.raises(ValidationError):
        HookEntry.model_validate(
            {
                "type": "command",
                "command": 'python3 "/path/to/validator.py"',
                "timeout": 30,
                "_dot_agent": {
                    "kit_id": 123,
                    "hook_id": "validator",
                },
            }
        )

    with pytest.raises(ValidationError):
        HookEntry.model_validate(
            {
                "type": "command",
                "command": 'python3 "/path/to/validator.py"',
                "timeout": 30,
                "_dot_agent": {
                    "kit_id": "my-kit",
                    "hook_id": 456,
                },
            }
        )


def test_hook_entry_roundtrip() -> None:
    """Test HookEntry serialization roundtrip."""
    metadata = HookMetadata(
        kit_id="my-kit",
        hook_id="validator",
    )

    original = HookEntry(
        type="command",
        command='python3 "/path/to/validator.py"',
        timeout=30,
        **{"_dot_agent": metadata},  # Use alias via unpacking
    )

    data = original.model_dump()
    restored = HookEntry.model_validate(data)

    assert restored.type == original.type
    assert restored.command == original.command
    assert restored.timeout == original.timeout
    assert restored.metadata.kit_id == original.metadata.kit_id
    assert restored.metadata.hook_id == original.metadata.hook_id
