"""Tests for hook installation and removal operations."""

from pathlib import Path

from dot_agent_kit.hooks.installer import install_hooks, remove_hooks
from dot_agent_kit.hooks.models import HookDefinition
from dot_agent_kit.hooks.settings import load_settings


def test_install_hooks_basic(tmp_project: Path) -> None:
    """Test installing a single hook to a project."""
    # Create kit with a hook script
    kit_path = tmp_project / "kit"
    kit_path.mkdir()
    script_path = kit_path / "hook.py"
    script_path.write_text("# Hook script", encoding="utf-8")

    # Define hook
    hook_def = HookDefinition(
        id="test-hook",
        lifecycle="UserPromptSubmit",
        matcher="**",
        script="hook.py",
        description="Test hook",
        timeout=30,
    )

    # Install hooks
    count = install_hooks(
        kit_id="test-kit",
        hooks=[hook_def],
        kit_path=kit_path,
        project_root=tmp_project,
    )

    # Verify installation
    assert count == 1

    # Check script copied
    installed_script = tmp_project / ".claude" / "hooks" / "test-kit" / "hook.py"
    assert installed_script.exists()
    assert installed_script.is_file()
    assert installed_script.read_text(encoding="utf-8") == "# Hook script"

    # Check settings.json updated
    settings_path = tmp_project / ".claude" / "settings.json"
    assert settings_path.exists()

    settings = load_settings(settings_path)
    assert settings.hooks is not None
    assert "UserPromptSubmit" in settings.hooks

    lifecycle_hooks = settings.hooks["UserPromptSubmit"]
    assert len(lifecycle_hooks) == 1
    assert lifecycle_hooks[0].matcher == "**"
    assert len(lifecycle_hooks[0].hooks) == 1

    hook_entry = lifecycle_hooks[0].hooks[0]
    expected_cmd = (
        "DOT_AGENT_KIT_ID=test-kit DOT_AGENT_HOOK_ID=test-hook "
        'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/test-kit/hook.py"'
    )
    assert hook_entry.command == expected_cmd
    assert hook_entry.timeout == 30


def test_install_multiple_hooks(tmp_project: Path) -> None:
    """Test installing multiple hooks with different lifecycles."""
    # Create kit with multiple hook scripts
    kit_path = tmp_project / "kit"
    kit_path.mkdir()

    (kit_path / "hook1.py").write_text("# Hook 1", encoding="utf-8")
    (kit_path / "hook2.py").write_text("# Hook 2", encoding="utf-8")
    (kit_path / "hook3.py").write_text("# Hook 3", encoding="utf-8")

    # Define hooks
    hooks = [
        HookDefinition(
            id="hook-1",
            lifecycle="UserPromptSubmit",
            matcher="**",
            script="hook1.py",
            description="Hook 1",
            timeout=30,
        ),
        HookDefinition(
            id="hook-2",
            lifecycle="UserPromptSubmit",
            matcher="*.py",
            script="hook2.py",
            description="Hook 2",
            timeout=45,
        ),
        HookDefinition(
            id="hook-3",
            lifecycle="PostToolUse",
            matcher="**",
            script="hook3.py",
            description="Hook 3",
            timeout=60,
        ),
    ]

    # Install hooks
    count = install_hooks(
        kit_id="multi-kit",
        hooks=hooks,
        kit_path=kit_path,
        project_root=tmp_project,
    )

    # Verify count
    assert count == 3

    # Check all scripts copied
    hooks_dir = tmp_project / ".claude" / "hooks" / "multi-kit"
    assert (hooks_dir / "hook1.py").exists()
    assert (hooks_dir / "hook2.py").exists()
    assert (hooks_dir / "hook3.py").exists()

    # Check settings structure
    settings = load_settings(tmp_project / ".claude" / "settings.json")
    assert settings.hooks is not None

    # Check user-prompt-submit lifecycle has 2 hooks
    submit_hooks = settings.hooks["UserPromptSubmit"]
    assert len(submit_hooks) == 2  # Two different matchers
    matchers = {group.matcher for group in submit_hooks}
    assert matchers == {"**", "*.py"}

    # Check PostToolUse lifecycle has 1 hook
    result_hooks = settings.hooks["PostToolUse"]
    assert len(result_hooks) == 1
    assert result_hooks[0].matcher == "**"


def test_install_hooks_missing_script(tmp_project: Path) -> None:
    """Test that hooks with missing scripts are skipped gracefully."""
    # Create kit with only one of two scripts
    kit_path = tmp_project / "kit"
    kit_path.mkdir()
    (kit_path / "exists.py").write_text("# Exists", encoding="utf-8")

    hooks = [
        HookDefinition(
            id="exists",
            lifecycle="UserPromptSubmit",
            matcher="**",
            script="exists.py",
            description="Exists",
            timeout=30,
        ),
        HookDefinition(
            id="missing",
            lifecycle="UserPromptSubmit",
            matcher="**",
            script="missing.py",
            description="Missing",
            timeout=30,
        ),
    ]

    # Install hooks
    count = install_hooks(
        kit_id="partial-kit",
        hooks=hooks,
        kit_path=kit_path,
        project_root=tmp_project,
    )

    # Only one hook should be installed
    assert count == 1

    # Check only existing script copied
    hooks_dir = tmp_project / ".claude" / "hooks" / "partial-kit"
    assert (hooks_dir / "exists.py").exists()
    assert not (hooks_dir / "missing.py").exists()

    # Check settings only has one hook
    settings = load_settings(tmp_project / ".claude" / "settings.json")
    assert settings.hooks is not None
    lifecycle_hooks = settings.hooks["UserPromptSubmit"]
    assert len(lifecycle_hooks) == 1
    assert len(lifecycle_hooks[0].hooks) == 1
    hook_entry = lifecycle_hooks[0].hooks[0]
    assert "DOT_AGENT_HOOK_ID=exists" in hook_entry.command


def test_install_hooks_replaces_existing(tmp_project: Path) -> None:
    """Test that reinstalling hooks removes old installation."""
    kit_path = tmp_project / "kit"
    kit_path.mkdir()

    # First installation
    (kit_path / "old.py").write_text("# Old", encoding="utf-8")
    old_hook = HookDefinition(
        id="old",
        lifecycle="UserPromptSubmit",
        matcher="**",
        script="old.py",
        description="Old",
        timeout=30,
    )
    install_hooks("test-kit", [old_hook], kit_path, tmp_project)

    # Verify old installation
    hooks_dir = tmp_project / ".claude" / "hooks" / "test-kit"
    assert (hooks_dir / "old.py").exists()

    # Second installation with different hook
    (kit_path / "new.py").write_text("# New", encoding="utf-8")
    new_hook = HookDefinition(
        id="new",
        lifecycle="PostToolUse",
        matcher="*.md",
        script="new.py",
        description="New",
        timeout=45,
    )
    count = install_hooks("test-kit", [new_hook], kit_path, tmp_project)

    assert count == 1

    # Old script should be removed
    assert not (hooks_dir / "old.py").exists()
    assert (hooks_dir / "new.py").exists()

    # Settings should only have new hook
    settings = load_settings(tmp_project / ".claude" / "settings.json")
    assert settings.hooks is not None

    # Old lifecycle should be gone (or contain other kits' hooks only)
    if "UserPromptSubmit" in settings.hooks:
        # Should not have our kit's hooks
        for group in settings.hooks["UserPromptSubmit"]:
            for hook in group.hooks:
                assert "DOT_AGENT_KIT_ID=test-kit" not in hook.command

    # New lifecycle should have the hook
    assert "PostToolUse" in settings.hooks
    result_hooks = settings.hooks["PostToolUse"]
    assert len(result_hooks) == 1
    hook_entry = result_hooks[0].hooks[0]
    assert "DOT_AGENT_HOOK_ID=new" in hook_entry.command


def test_install_hooks_empty_list(tmp_project: Path) -> None:
    """Test installing with empty hooks list."""
    kit_path = tmp_project / "kit"
    kit_path.mkdir()

    count = install_hooks(
        kit_id="empty-kit",
        hooks=[],
        kit_path=kit_path,
        project_root=tmp_project,
    )

    assert count == 0

    # No hooks directory should be created
    hooks_dir = tmp_project / ".claude" / "hooks" / "empty-kit"
    assert not hooks_dir.exists()

    # Settings.json should not be created if it didn't exist
    settings_path = tmp_project / ".claude" / "settings.json"
    if settings_path.exists():
        settings = load_settings(settings_path)
        # Should be empty or not have hooks from this kit
        if settings.hooks is not None:
            for lifecycle_groups in settings.hooks.values():
                for group in lifecycle_groups:
                    for hook in group.hooks:
                        assert "DOT_AGENT_KIT_ID=empty-kit" not in hook.command


def test_install_hooks_creates_directories(tmp_project: Path) -> None:
    """Test that installation creates necessary directories."""
    # Start with no .claude directory
    claude_dir = tmp_project / ".claude"
    assert not claude_dir.exists()

    kit_path = tmp_project / "kit"
    kit_path.mkdir()
    (kit_path / "hook.py").write_text("# Hook", encoding="utf-8")

    hook = HookDefinition(
        id="test",
        lifecycle="UserPromptSubmit",
        matcher="**",
        script="hook.py",
        description="Test",
        timeout=30,
    )

    install_hooks("test-kit", [hook], kit_path, tmp_project)

    # All directories should be created
    assert claude_dir.exists()
    assert (claude_dir / "hooks").exists()
    assert (claude_dir / "hooks" / "test-kit").exists()
    assert (claude_dir / "settings.json").exists()


def test_install_hooks_flattens_nested_scripts(tmp_project: Path) -> None:
    """Test that nested script paths are flattened in installation."""
    kit_path = tmp_project / "kit"
    nested_dir = kit_path / "scripts" / "subdir"
    nested_dir.mkdir(parents=True)

    script_path = nested_dir / "nested_hook.py"
    script_path.write_text("# Nested hook", encoding="utf-8")

    hook = HookDefinition(
        id="nested",
        lifecycle="UserPromptSubmit",
        matcher="**",
        script="scripts/subdir/nested_hook.py",
        description="Nested",
        timeout=30,
    )

    install_hooks("test-kit", [hook], kit_path, tmp_project)

    # Script should be at flattened location
    hooks_dir = tmp_project / ".claude" / "hooks" / "test-kit"
    flattened_script = hooks_dir / "nested_hook.py"
    assert flattened_script.exists()
    assert not (hooks_dir / "scripts").exists()  # No nested structure

    # Command should reference flattened location using $CLAUDE_PROJECT_DIR
    settings = load_settings(tmp_project / ".claude" / "settings.json")
    assert settings.hooks is not None
    hook_entry = settings.hooks["UserPromptSubmit"][0].hooks[0]
    expected_cmd = (
        "DOT_AGENT_KIT_ID=test-kit DOT_AGENT_HOOK_ID=nested "
        'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/test-kit/nested_hook.py"'
    )
    assert hook_entry.command == expected_cmd


def test_remove_hooks_basic(tmp_project: Path) -> None:
    """Test removing hooks from a project."""
    # Install hooks first
    kit_path = tmp_project / "kit"
    kit_path.mkdir()
    (kit_path / "hook.py").write_text("# Hook", encoding="utf-8")

    hook = HookDefinition(
        id="test",
        lifecycle="UserPromptSubmit",
        matcher="**",
        script="hook.py",
        description="Test",
        timeout=30,
    )
    install_hooks("test-kit", [hook], kit_path, tmp_project)

    # Verify installation
    hooks_dir = tmp_project / ".claude" / "hooks" / "test-kit"
    assert hooks_dir.exists()

    # Remove hooks
    count = remove_hooks("test-kit", tmp_project)

    assert count == 1

    # Directory should be deleted
    assert not hooks_dir.exists()

    # Settings should not contain the hook
    settings = load_settings(tmp_project / ".claude" / "settings.json")
    if settings.hooks is not None and "UserPromptSubmit" in settings.hooks:
        for group in settings.hooks["UserPromptSubmit"]:
            for hook_entry in group.hooks:
                assert "DOT_AGENT_KIT_ID=test-kit" not in hook_entry.command


def test_remove_hooks_preserves_other_kits(tmp_project: Path) -> None:
    """Test that removing one kit's hooks preserves other kits."""
    kit_path = tmp_project / "kit"
    kit_path.mkdir()

    # Install hooks from two kits
    (kit_path / "hook_a.py").write_text("# A", encoding="utf-8")
    (kit_path / "hook_b.py").write_text("# B", encoding="utf-8")

    hook_a = HookDefinition(
        id="hook-a",
        lifecycle="UserPromptSubmit",
        matcher="**",
        script="hook_a.py",
        description="A",
        timeout=30,
    )
    hook_b = HookDefinition(
        id="hook-b",
        lifecycle="UserPromptSubmit",
        matcher="**",
        script="hook_b.py",
        description="B",
        timeout=30,
    )

    install_hooks("kit-a", [hook_a], kit_path, tmp_project)
    install_hooks("kit-b", [hook_b], kit_path, tmp_project)

    # Remove kit-a
    count = remove_hooks("kit-a", tmp_project)

    assert count == 1

    # kit-a directory deleted
    assert not (tmp_project / ".claude" / "hooks" / "kit-a").exists()

    # kit-b directory intact
    assert (tmp_project / ".claude" / "hooks" / "kit-b").exists()

    # Settings should only have kit-b
    settings = load_settings(tmp_project / ".claude" / "settings.json")
    assert settings.hooks is not None
    lifecycle_hooks = settings.hooks["UserPromptSubmit"]

    # Count hooks from each kit
    kit_a_count = sum(
        1
        for group in lifecycle_hooks
        for hook in group.hooks
        if "DOT_AGENT_KIT_ID=kit-a" in hook.command
    )
    kit_b_count = sum(
        1
        for group in lifecycle_hooks
        for hook in group.hooks
        if "DOT_AGENT_KIT_ID=kit-b" in hook.command
    )

    assert kit_a_count == 0
    assert kit_b_count == 1


def test_remove_hooks_nonexistent_kit(tmp_project: Path) -> None:
    """Test removing hooks for a kit that was never installed."""
    count = remove_hooks("nonexistent-kit", tmp_project)

    assert count == 0

    # Should not crash or create files
    settings_path = tmp_project / ".claude" / "settings.json"
    if settings_path.exists():
        # Settings should be unchanged
        settings = load_settings(settings_path)
        if settings.hooks is not None:
            for lifecycle_groups in settings.hooks.values():
                for group in lifecycle_groups:
                    for hook in group.hooks:
                        assert "DOT_AGENT_KIT_ID=nonexistent-kit" not in hook.command


def test_remove_hooks_cleans_empty_lifecycles(tmp_project: Path) -> None:
    """Test that removing the last hook from a lifecycle removes the lifecycle."""
    kit_path = tmp_project / "kit"
    kit_path.mkdir()
    (kit_path / "hook.py").write_text("# Hook", encoding="utf-8")

    hook = HookDefinition(
        id="test",
        lifecycle="UserPromptSubmit",
        matcher="**",
        script="hook.py",
        description="Test",
        timeout=30,
    )

    install_hooks("test-kit", [hook], kit_path, tmp_project)
    remove_hooks("test-kit", tmp_project)

    # Settings should not have the lifecycle anymore
    settings = load_settings(tmp_project / ".claude" / "settings.json")
    if settings.hooks is not None:
        assert (
            "UserPromptSubmit" not in settings.hooks or len(settings.hooks["UserPromptSubmit"]) == 0
        )


def test_hook_entry_metadata_roundtrip(tmp_project: Path) -> None:
    """Test that hook metadata survives JSON serialization roundtrip."""
    kit_path = tmp_project / "kit"
    kit_path.mkdir()
    (kit_path / "hook.py").write_text("# Hook", encoding="utf-8")

    hook = HookDefinition(
        id="metadata-test",
        lifecycle="UserPromptSubmit",
        matcher="**",
        script="hook.py",
        description="Metadata test",
        timeout=30,
    )

    install_hooks("metadata-kit", [hook], kit_path, tmp_project)

    # Read raw JSON to check env vars in command
    settings_path = tmp_project / ".claude" / "settings.json"
    raw_json = settings_path.read_text(encoding="utf-8")
    assert "DOT_AGENT_KIT_ID=metadata-kit" in raw_json
    assert "DOT_AGENT_HOOK_ID=metadata-test" in raw_json

    # Load and verify structure
    settings = load_settings(settings_path)
    assert settings.hooks is not None

    hook_entry = settings.hooks["UserPromptSubmit"][0].hooks[0]
    assert "DOT_AGENT_KIT_ID=metadata-kit" in hook_entry.command
    assert "DOT_AGENT_HOOK_ID=metadata-test" in hook_entry.command

    # Re-save and re-load to ensure roundtrip works
    from dot_agent_kit.hooks.settings import save_settings

    save_settings(settings_path, settings)
    reloaded_settings = load_settings(settings_path)

    assert reloaded_settings.hooks is not None
    reloaded_entry = reloaded_settings.hooks["UserPromptSubmit"][0].hooks[0]
    assert "DOT_AGENT_KIT_ID=metadata-kit" in reloaded_entry.command
    assert "DOT_AGENT_HOOK_ID=metadata-test" in reloaded_entry.command


def test_install_hook_without_matcher(tmp_project: Path) -> None:
    """Test installing a hook without matcher field uses wildcard default."""
    # Create kit with a hook script
    kit_path = tmp_project / "kit"
    kit_path.mkdir()
    script_path = kit_path / "hook.py"
    script_path.write_text("# Hook script", encoding="utf-8")

    # Define hook without matcher
    hook_def = HookDefinition(
        id="test-hook",
        lifecycle="UserPromptSubmit",
        script="hook.py",
        description="Test hook without matcher",
        timeout=30,
    )

    # Install hooks
    count = install_hooks(
        kit_id="test-kit",
        hooks=[hook_def],
        kit_path=kit_path,
        project_root=tmp_project,
    )

    # Verify installation
    assert count == 1

    # Check settings.json uses wildcard matcher
    settings_path = tmp_project / ".claude" / "settings.json"
    assert settings_path.exists()

    settings = load_settings(settings_path)
    assert settings.hooks is not None
    assert "UserPromptSubmit" in settings.hooks

    lifecycle_hooks = settings.hooks["UserPromptSubmit"]
    assert len(lifecycle_hooks) == 1
    assert lifecycle_hooks[0].matcher == "*"  # Should default to wildcard
    assert len(lifecycle_hooks[0].hooks) == 1

    hook_entry = lifecycle_hooks[0].hooks[0]
    assert "DOT_AGENT_KIT_ID=test-kit" in hook_entry.command
    assert "DOT_AGENT_HOOK_ID=test-hook" in hook_entry.command


def test_install_hooks_includes_type_field(tmp_project: Path) -> None:
    """Test that installed hooks include a 'type' field for Claude Code compatibility.

    Claude Code requires hooks to have a 'type' discriminator field with value
    'command' or 'prompt'. This test ensures generated hooks are valid.
    """
    # Create kit with a hook script
    kit_path = tmp_project / "kit"
    kit_path.mkdir()
    script_path = kit_path / "hook.py"
    script_path.write_text("# Hook script", encoding="utf-8")

    # Define hook
    hook_def = HookDefinition(
        id="test-hook",
        lifecycle="UserPromptSubmit",
        matcher="**",
        script="hook.py",
        description="Test hook",
        timeout=30,
    )

    # Install hooks
    count = install_hooks(
        kit_id="test-kit",
        hooks=[hook_def],
        kit_path=kit_path,
        project_root=tmp_project,
    )

    assert count == 1

    # Load settings and get hook entry
    settings = load_settings(tmp_project / ".claude" / "settings.json")
    assert settings.hooks is not None
    assert "UserPromptSubmit" in settings.hooks

    hook_entry = settings.hooks["UserPromptSubmit"][0].hooks[0]

    # Verify type field exists and has correct value
    assert hasattr(hook_entry, "type"), "Hook entry must have 'type' field for Claude Code"
    assert hook_entry.type == "command", "Hook type should be 'command' for shell commands"
