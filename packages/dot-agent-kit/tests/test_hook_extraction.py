"""Tests for hook ID extraction from settings.json commands."""

from dot_agent_kit.commands.check import _extract_hooks_for_kit
from dot_agent_kit.hooks.models import ClaudeSettings, HookEntry, MatcherGroup


def test_extract_hooks_extracts_hook_id_from_command() -> None:
    """Test that hook ID is correctly extracted from DOT_AGENT_HOOK_ID env var.

    This is a regression test for the bug where _extract_hooks_for_kit would
    use kit_id as fallback instead of extracting the actual hook ID from the
    DOT_AGENT_HOOK_ID environment variable in the command string.
    """
    # Setup: Create settings with a hook that has DOT_AGENT_HOOK_ID
    hook_entry = HookEntry(
        type="command",
        command=(
            "DOT_AGENT_KIT_ID=my-kit DOT_AGENT_HOOK_ID=my-hook "
            'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/my-kit/script.py"'
        ),
        timeout=30,
    )

    hook_group = MatcherGroup(
        matcher="*",
        hooks=[hook_entry],
    )

    settings = ClaudeSettings(
        permissions=None,
        hooks={
            "UserPromptSubmit": [hook_group],
        },
    )

    # Execute: Extract hooks for "my-kit"
    extracted_hooks = _extract_hooks_for_kit(settings, "my-kit")

    # Verify: Should extract "my-hook" as hook_id, NOT "my-kit"
    assert len(extracted_hooks) == 1, "Should extract one hook"
    assert extracted_hooks[0].hook_id == "my-hook", (
        f"Expected hook_id 'my-hook', got '{extracted_hooks[0].hook_id}'. "
        "Hook ID should be extracted from DOT_AGENT_HOOK_ID env var, not fallback to kit_id"
    )
    assert extracted_hooks[0].lifecycle == "UserPromptSubmit"
    assert extracted_hooks[0].timeout == 30


def test_extract_hooks_fails_without_hook_id() -> None:
    """Test that extraction fails hard when DOT_AGENT_HOOK_ID is missing.

    Old format commands that don't have DOT_AGENT_HOOK_ID should cause an error,
    not silently fall back to using kit_id as hook_id.
    """
    # Setup: Create settings with old format (no DOT_AGENT_HOOK_ID)
    hook_entry = HookEntry(
        type="command",
        command=(
            'DOT_AGENT_KIT_ID=my-kit python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/my-kit/script.py"'
        ),
        timeout=30,
    )

    hook_group = MatcherGroup(
        matcher="*",
        hooks=[hook_entry],
    )

    settings = ClaudeSettings(
        permissions=None,
        hooks={
            "UserPromptSubmit": [hook_group],
        },
    )

    # Execute & Verify: Should raise ValueError for old format
    try:
        _extract_hooks_for_kit(settings, "my-kit")
        raise AssertionError("Should have raised ValueError for missing DOT_AGENT_HOOK_ID")
    except ValueError as e:
        assert "DOT_AGENT_HOOK_ID" in str(e), "Error should mention missing DOT_AGENT_HOOK_ID"


def test_extract_hooks_handles_multiple_hooks_for_same_kit() -> None:
    """Test extraction of multiple hooks from the same kit."""
    # Setup: Create settings with multiple hooks
    hook1 = HookEntry(
        type="command",
        command=(
            "DOT_AGENT_KIT_ID=my-kit DOT_AGENT_HOOK_ID=hook-1 "
            'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/my-kit/h1.py"'
        ),
        timeout=30,
    )
    hook2 = HookEntry(
        type="command",
        command=(
            "DOT_AGENT_KIT_ID=my-kit DOT_AGENT_HOOK_ID=hook-2 "
            'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/my-kit/h2.py"'
        ),
        timeout=60,
    )

    hook_group = MatcherGroup(
        matcher="*",
        hooks=[hook1, hook2],
    )

    settings = ClaudeSettings(
        permissions=None,
        hooks={
            "UserPromptSubmit": [hook_group],
        },
    )

    # Execute: Extract hooks for "my-kit"
    extracted_hooks = _extract_hooks_for_kit(settings, "my-kit")

    # Verify: Should extract both hooks with correct IDs
    assert len(extracted_hooks) == 2, "Should extract two hooks"

    hook_ids = {hook.hook_id for hook in extracted_hooks}
    assert hook_ids == {"hook-1", "hook-2"}, f"Expected hook IDs {{hook-1, hook-2}}, got {hook_ids}"


def test_extract_hooks_ignores_other_kits() -> None:
    """Test that extraction only returns hooks for the specified kit."""
    # Setup: Create settings with hooks from different kits
    hook1 = HookEntry(
        type="command",
        command=(
            "DOT_AGENT_KIT_ID=kit-a DOT_AGENT_HOOK_ID=hook-a "
            'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/kit-a/script.py"'
        ),
        timeout=30,
    )
    hook2 = HookEntry(
        type="command",
        command=(
            "DOT_AGENT_KIT_ID=kit-b DOT_AGENT_HOOK_ID=hook-b "
            'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/kit-b/script.py"'
        ),
        timeout=30,
    )

    hook_group = MatcherGroup(
        matcher="*",
        hooks=[hook1, hook2],
    )

    settings = ClaudeSettings(
        permissions=None,
        hooks={
            "UserPromptSubmit": [hook_group],
        },
    )

    # Execute: Extract hooks for "kit-a" only
    extracted_hooks = _extract_hooks_for_kit(settings, "kit-a")

    # Verify: Should only extract hook-a
    assert len(extracted_hooks) == 1, "Should extract only one hook for kit-a"
    assert extracted_hooks[0].hook_id == "hook-a"
