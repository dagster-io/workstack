"""Tests for settings models."""

import pytest

from dot_agent_kit.models.settings import ClaudeSettings, MatcherGroup


def test_matcher_group_creation() -> None:
    """Test MatcherGroup creation."""
    group = MatcherGroup(
        matcher="Bash",
        hooks=[
            {
                "type": "command",
                "command": "python3 test.py",
                "timeout": 30,
            }
        ],
    )

    assert group.matcher == "Bash"
    assert len(group.hooks) == 1
    assert group.hooks[0]["type"] == "command"


def test_matcher_group_to_dict() -> None:
    """Test MatcherGroup conversion to dict."""
    group = MatcherGroup(
        matcher="Write|Edit",
        hooks=[
            {"type": "command", "command": "python3 test.py", "timeout": 30},
            {"type": "command", "command": "python3 test2.py", "timeout": 60},
        ],
    )

    result = group.model_dump()

    assert result["matcher"] == "Write|Edit"
    hooks = result["hooks"]
    if not isinstance(hooks, list):
        msg = "hooks should be a list"
        raise AssertionError(msg)
    assert len(hooks) == 2
    assert hooks[0]["command"] == "python3 test.py"


def test_matcher_group_from_dict() -> None:
    """Test MatcherGroup parsing from dict."""
    data = {
        "matcher": "Bash",
        "hooks": [
            {"type": "command", "command": "python3 test.py", "timeout": 30},
        ],
    }

    group = MatcherGroup.model_validate(data)

    assert group.matcher == "Bash"
    assert len(group.hooks) == 1
    assert group.hooks[0]["command"] == "python3 test.py"


def test_matcher_group_from_dict_invalid_types() -> None:
    """Test MatcherGroup.from_dict with invalid types."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        MatcherGroup.model_validate({"matcher": 123, "hooks": []})

    with pytest.raises(ValidationError):
        MatcherGroup.model_validate({"matcher": "Bash", "hooks": "not a list"})


def test_claude_settings_empty() -> None:
    """Test ClaudeSettings.empty() creates empty settings."""
    settings = ClaudeSettings.empty()

    assert settings.hooks == {}
    assert settings.other == {}


def test_claude_settings_to_dict_empty() -> None:
    """Test ClaudeSettings.model_dump() with empty settings."""
    settings = ClaudeSettings.empty()
    result = settings.model_dump()

    assert result == {"hooks": {}}


def test_claude_settings_to_dict_with_hooks() -> None:
    """Test ClaudeSettings.model_dump() with hooks."""
    group = MatcherGroup(
        matcher="Bash", hooks=[{"type": "command", "command": "test", "timeout": 30}]
    )

    settings = ClaudeSettings(hooks={"PreToolUse": [group]})

    result = settings.model_dump()

    assert "hooks" in result
    hooks = result["hooks"]
    if not isinstance(hooks, dict):
        msg = "hooks should be a dict"
        raise AssertionError(msg)
    assert "PreToolUse" in hooks
    pre_tool_use = hooks["PreToolUse"]
    if not isinstance(pre_tool_use, list):
        msg = "PreToolUse should be a list"
        raise AssertionError(msg)
    assert len(pre_tool_use) == 1
    assert pre_tool_use[0]["matcher"] == "Bash"


def test_claude_settings_to_dict_preserves_other() -> None:
    """Test ClaudeSettings.model_dump() preserves other settings."""
    settings = ClaudeSettings.model_validate(
        {
            "hooks": {},
            "some_setting": "value",
            "another_setting": {"nested": "data"},
        }
    )

    result = settings.model_dump()

    assert result["some_setting"] == "value"
    another_setting = result["another_setting"]
    if not isinstance(another_setting, dict):
        msg = "another_setting should be a dict"
        raise AssertionError(msg)
    assert another_setting["nested"] == "data"


def test_claude_settings_from_dict_empty() -> None:
    """Test ClaudeSettings.model_validate() with empty dict."""
    settings = ClaudeSettings.model_validate({})

    assert settings.hooks == {}
    assert settings.other == {}


def test_claude_settings_from_dict_with_hooks() -> None:
    """Test ClaudeSettings.model_validate() with hooks."""
    data: dict[str, object] = {
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

    settings = ClaudeSettings.model_validate(data)

    assert "PreToolUse" in settings.hooks
    assert len(settings.hooks["PreToolUse"]) == 1
    assert settings.hooks["PreToolUse"][0].matcher == "Bash"


def test_claude_settings_from_dict_preserves_other() -> None:
    """Test ClaudeSettings.model_validate() preserves other settings."""
    data: dict[str, object] = {
        "hooks": {},
        "some_setting": "value",
        "another_setting": {"nested": "data"},
    }

    settings = ClaudeSettings.model_validate(data)

    assert settings.other["some_setting"] == "value"
    another_setting = settings.other["another_setting"]
    if not isinstance(another_setting, dict):
        msg = "another_setting should be a dict"
        raise AssertionError(msg)
    assert another_setting["nested"] == "data"


def test_claude_settings_from_dict_invalid_hooks_type() -> None:
    """Test ClaudeSettings.model_validate() with invalid hooks type."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ClaudeSettings.model_validate({"hooks": "not a dict"})


def test_claude_settings_from_dict_invalid_lifecycle_type() -> None:
    """Test ClaudeSettings.model_validate() with invalid lifecycle type."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ClaudeSettings.model_validate({"hooks": {"PreToolUse": "not a list"}})


def test_claude_settings_roundtrip() -> None:
    """Test ClaudeSettings serialization roundtrip."""
    original = ClaudeSettings.model_validate(
        {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [{"type": "command", "command": "test1", "timeout": 30}],
                    }
                ],
                "PostToolUse": [
                    {
                        "matcher": "Write|Edit",
                        "hooks": [{"type": "command", "command": "test2", "timeout": 60}],
                    }
                ],
            },
            "custom_setting": "value",
        }
    )

    data = original.model_dump()
    restored = ClaudeSettings.model_validate(data)

    assert len(restored.hooks) == 2
    assert "PreToolUse" in restored.hooks
    assert "PostToolUse" in restored.hooks
    assert restored.hooks["PreToolUse"][0].matcher == "Bash"
    assert restored.hooks["PostToolUse"][0].matcher == "Write|Edit"
    assert restored.other["custom_setting"] == "value"


def test_claude_settings_from_dict_rejects_non_dict_groups() -> None:
    """Test ClaudeSettings.model_validate() rejects non-dict entries in hooks array."""
    from pydantic import ValidationError

    data: dict[str, object] = {
        "hooks": {
            "PreToolUse": [
                {"matcher": "Bash", "hooks": []},
                "not a dict",
                {"matcher": "Write", "hooks": []},
            ]
        }
    }

    # Pydantic validates strictly and will reject invalid data
    with pytest.raises(ValidationError):
        ClaudeSettings.model_validate(data)
