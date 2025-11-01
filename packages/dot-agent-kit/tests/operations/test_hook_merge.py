"""Tests for hook merge operations."""

from dot_agent_kit.models.settings import ClaudeSettings, MatcherGroup
from dot_agent_kit.operations.hook_merge import (
    add_hook_to_settings,
    cleanup_empty_groups,
    find_or_create_matcher_group,
    merge_hooks_into_groups,
)


def test_find_or_create_matcher_group_existing() -> None:
    """Test finding an existing matcher group."""
    groups = [
        MatcherGroup(matcher="Bash", hooks=[]),
        MatcherGroup(matcher="Write|Edit", hooks=[]),
    ]

    group = find_or_create_matcher_group(groups, "Bash")

    assert group.matcher == "Bash"
    assert group in groups


def test_find_or_create_matcher_group_new() -> None:
    """Test creating a new matcher group."""
    groups = [
        MatcherGroup(matcher="Bash", hooks=[]),
    ]

    group = find_or_create_matcher_group(groups, "Write|Edit")

    assert group.matcher == "Write|Edit"
    assert group.hooks == []
    assert group not in groups


def test_add_hook_to_settings_new_lifecycle() -> None:
    """Test adding hook to a new lifecycle."""
    settings = ClaudeSettings.empty()
    hook: dict[str, object] = {"type": "command", "command": "test"}

    result = add_hook_to_settings(settings, "PreToolUse", "Bash", hook)

    assert "PreToolUse" in result.hooks
    assert len(result.hooks["PreToolUse"]) == 1
    assert result.hooks["PreToolUse"][0].matcher == "Bash"
    assert hook in result.hooks["PreToolUse"][0].hooks


def test_add_hook_to_settings_existing_matcher() -> None:
    """Test adding hook to existing matcher group."""
    existing_hook: dict[str, object] = {"type": "command", "command": "existing"}
    group = MatcherGroup(matcher="Bash", hooks=[existing_hook])
    settings = ClaudeSettings(hooks={"PreToolUse": [group]})

    new_hook: dict[str, object] = {"type": "command", "command": "new"}
    result = add_hook_to_settings(settings, "PreToolUse", "Bash", new_hook)

    assert len(result.hooks["PreToolUse"]) == 1
    assert len(result.hooks["PreToolUse"][0].hooks) == 2
    assert existing_hook in result.hooks["PreToolUse"][0].hooks
    assert new_hook in result.hooks["PreToolUse"][0].hooks


def test_add_hook_to_settings_new_matcher() -> None:
    """Test adding hook with new matcher to existing lifecycle."""
    existing_group = MatcherGroup(matcher="Bash", hooks=[])
    settings = ClaudeSettings(hooks={"PreToolUse": [existing_group]})

    new_hook: dict[str, object] = {"type": "command", "command": "new"}
    result = add_hook_to_settings(settings, "PreToolUse", "Write|Edit", new_hook)

    assert len(result.hooks["PreToolUse"]) == 2
    matchers = {g.matcher for g in result.hooks["PreToolUse"]}
    assert matchers == {"Bash", "Write|Edit"}


def test_merge_hooks_into_groups_single_matcher() -> None:
    """Test merging hooks with single matcher."""
    hook1: dict[str, object] = {
        "type": "command",
        "command": "test1",
        "timeout": 30,
        "_dot_agent": {"kit_id": "kit1", "hook_id": "hook1"},
    }
    hook2: dict[str, object] = {
        "type": "command",
        "command": "test2",
        "timeout": 30,
        "_dot_agent": {"kit_id": "kit2", "hook_id": "hook2"},
    }

    group1 = MatcherGroup(matcher="Bash", hooks=[hook1])
    group2 = MatcherGroup(matcher="Bash", hooks=[hook2])

    settings = ClaudeSettings(hooks={"PreToolUse": [group1, group2]})

    result = merge_hooks_into_groups(settings)

    assert len(result.hooks["PreToolUse"]) == 1
    assert result.hooks["PreToolUse"][0].matcher == "Bash"
    assert len(result.hooks["PreToolUse"][0].hooks) == 2
    assert hook1 in result.hooks["PreToolUse"][0].hooks
    assert hook2 in result.hooks["PreToolUse"][0].hooks


def test_merge_hooks_into_groups_multiple_matchers() -> None:
    """Test merging hooks preserves different matchers."""
    bash_hook: dict[str, object] = {
        "type": "command",
        "command": "bash_test",
        "timeout": 30,
        "_dot_agent": {"kit_id": "kit1", "hook_id": "hook1"},
    }
    write_hook: dict[str, object] = {
        "type": "command",
        "command": "write_test",
        "timeout": 30,
        "_dot_agent": {"kit_id": "kit2", "hook_id": "hook2"},
    }

    group1 = MatcherGroup(matcher="Bash", hooks=[bash_hook])
    group2 = MatcherGroup(matcher="Write|Edit", hooks=[write_hook])

    settings = ClaudeSettings(hooks={"PreToolUse": [group1, group2]})

    result = merge_hooks_into_groups(settings)

    assert len(result.hooks["PreToolUse"]) == 2
    matchers = {g.matcher for g in result.hooks["PreToolUse"]}
    assert matchers == {"Bash", "Write|Edit"}


def test_merge_hooks_into_groups_multiple_lifecycles() -> None:
    """Test merging hooks across multiple lifecycles."""
    pre_hook: dict[str, object] = {
        "type": "command",
        "command": "pre_test",
        "timeout": 30,
        "_dot_agent": {"kit_id": "kit1", "hook_id": "hook1"},
    }
    post_hook: dict[str, object] = {
        "type": "command",
        "command": "post_test",
        "timeout": 30,
        "_dot_agent": {"kit_id": "kit2", "hook_id": "hook2"},
    }

    settings = ClaudeSettings(
        hooks={
            "PreToolUse": [MatcherGroup(matcher="Bash", hooks=[pre_hook])],
            "PostToolUse": [MatcherGroup(matcher="Write", hooks=[post_hook])],
        },
    )

    result = merge_hooks_into_groups(settings)

    assert len(result.hooks) == 2
    assert "PreToolUse" in result.hooks
    assert "PostToolUse" in result.hooks


def test_merge_hooks_preserves_other_settings() -> None:
    """Test merge operation preserves non-hook settings."""
    settings = ClaudeSettings.model_validate(
        {
            "hooks": {},
            "custom": "value",
            "nested": {"key": "data"},
        }
    )

    result = merge_hooks_into_groups(settings)

    assert result.other["custom"] == "value"
    nested = result.other["nested"]
    if not isinstance(nested, dict):
        msg = "nested should be a dict"
        raise AssertionError(msg)
    assert nested["key"] == "data"


def test_cleanup_empty_groups_removes_empty() -> None:
    """Test cleanup removes groups with no hooks."""
    settings = ClaudeSettings(
        hooks={
            "PreToolUse": [
                MatcherGroup(matcher="Bash", hooks=[]),
                MatcherGroup(matcher="Write", hooks=[{"cmd": "test"}]),
            ]
        },
    )

    result = cleanup_empty_groups(settings)

    assert len(result.hooks["PreToolUse"]) == 1
    assert result.hooks["PreToolUse"][0].matcher == "Write"


def test_cleanup_empty_groups_removes_empty_lifecycle() -> None:
    """Test cleanup removes lifecycle with only empty groups."""
    settings = ClaudeSettings(
        hooks={
            "PreToolUse": [MatcherGroup(matcher="Bash", hooks=[])],
            "PostToolUse": [MatcherGroup(matcher="Write", hooks=[{"cmd": "test"}])],
        },
    )

    result = cleanup_empty_groups(settings)

    assert "PreToolUse" not in result.hooks
    assert "PostToolUse" in result.hooks


def test_cleanup_empty_groups_empty_settings() -> None:
    """Test cleanup on empty settings."""
    settings = ClaudeSettings.empty()

    result = cleanup_empty_groups(settings)

    assert result.hooks == {}
