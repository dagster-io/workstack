"""Tests for hook installation operations."""

from pathlib import Path

from dot_agent_kit.io.settings_json import load_settings
from dot_agent_kit.models.hook import HookDefinition
from dot_agent_kit.operations.hook_install import (
    build_hook_command,
    copy_hook_scripts,
    install_hooks,
)


def test_build_hook_command() -> None:
    """Test building hook command string."""
    script_path = Path("/path/to/hook.py")

    command = build_hook_command(script_path)

    assert command.startswith('python3 "')
    assert command.endswith('"')
    assert "hook.py" in command


def test_copy_hook_scripts(tmp_path: Path) -> None:
    """Test copying hook scripts to destination."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    hook_script = source_dir / "hooks" / "validator.py"
    hook_script.parent.mkdir()
    hook_script.write_text("# hook script", encoding="utf-8")

    dest_dir = tmp_path / "dest"

    hook_def = HookDefinition(
        hook_id="validator",
        lifecycle="PreToolUse",
        matcher="Bash",
        script="hooks/validator.py",
        description="Validator",
    )

    copy_hook_scripts([hook_def], source_dir, dest_dir)

    assert (dest_dir / "validator.py").exists()
    assert (dest_dir / "validator.py").read_text(encoding="utf-8") == "# hook script"


def test_copy_hook_scripts_missing_source(tmp_path: Path) -> None:
    """Test copy_hook_scripts raises error for missing source."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_dir = tmp_path / "dest"

    hook_def = HookDefinition(
        hook_id="validator",
        lifecycle="PreToolUse",
        matcher="Bash",
        script="hooks/missing.py",
        description="Missing",
    )

    try:
        copy_hook_scripts([hook_def], source_dir, dest_dir)
        msg = "Expected FileNotFoundError"
        raise AssertionError(msg)
    except FileNotFoundError as e:
        assert "Hook script not found" in str(e)


def test_install_hooks_basic(tmp_path: Path) -> None:
    """Test basic hook installation."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    hook_script = source_dir / "hooks" / "validator.py"
    hook_script.parent.mkdir()
    hook_script.write_text("# validator", encoding="utf-8")

    claude_dir = tmp_path / ".claude"
    settings_path = claude_dir / "settings.json"

    hook_def = HookDefinition(
        hook_id="validator",
        lifecycle="PreToolUse",
        matcher="Bash",
        script="hooks/validator.py",
        description="Validate bash commands",
        timeout=30,
    )

    def mock_get_settings_path() -> Path:
        return settings_path

    def mock_get_hooks_dir(kit_name: str) -> Path:
        return claude_dir / "hooks" / kit_name

    import dot_agent_kit.operations.hook_install as hook_install_module

    original_get_settings = hook_install_module.get_settings_path
    original_get_hooks = hook_install_module.get_hooks_dir

    try:
        hook_install_module.get_settings_path = mock_get_settings_path
        hook_install_module.get_hooks_dir = mock_get_hooks_dir

        installed_ids = install_hooks(
            kit_id="my-kit",
            hook_definitions=[hook_def],
            source_dir=source_dir,
        )

        assert installed_ids == ["validator"]

        assert (claude_dir / "hooks" / "my-kit" / "validator.py").exists()

        assert settings_path.exists()
        settings = load_settings(settings_path)

        assert "PreToolUse" in settings.hooks
        assert len(settings.hooks["PreToolUse"]) == 1
        assert settings.hooks["PreToolUse"][0].matcher == "Bash"
        assert len(settings.hooks["PreToolUse"][0].hooks) == 1

        hook_entry = settings.hooks["PreToolUse"][0].hooks[0]
        assert hook_entry["type"] == "command"
        assert "validator.py" in hook_entry["command"]  # type: ignore[operator]
        assert hook_entry["timeout"] == 30

        metadata = hook_entry["_dot_agent"]
        assert isinstance(metadata, dict)
        assert metadata["kit_id"] == "my-kit"
        assert metadata["hook_id"] == "validator"

    finally:
        hook_install_module.get_settings_path = original_get_settings
        hook_install_module.get_hooks_dir = original_get_hooks


def test_install_hooks_multiple(tmp_path: Path) -> None:
    """Test installing multiple hooks."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    (source_dir / "hooks").mkdir()
    (source_dir / "hooks" / "validator.py").write_text("# validator", encoding="utf-8")
    (source_dir / "hooks" / "formatter.py").write_text("# formatter", encoding="utf-8")

    claude_dir = tmp_path / ".claude"
    settings_path = claude_dir / "settings.json"

    hooks = [
        HookDefinition(
            hook_id="validator",
            lifecycle="PreToolUse",
            matcher="Bash",
            script="hooks/validator.py",
            description="Validate",
        ),
        HookDefinition(
            hook_id="formatter",
            lifecycle="PostToolUse",
            matcher="Write|Edit",
            script="hooks/formatter.py",
            description="Format",
        ),
    ]

    def mock_get_settings_path() -> Path:
        return settings_path

    def mock_get_hooks_dir(kit_name: str) -> Path:
        return claude_dir / "hooks" / kit_name

    import dot_agent_kit.operations.hook_install as hook_install_module

    original_get_settings = hook_install_module.get_settings_path
    original_get_hooks = hook_install_module.get_hooks_dir

    try:
        hook_install_module.get_settings_path = mock_get_settings_path
        hook_install_module.get_hooks_dir = mock_get_hooks_dir

        installed_ids = install_hooks(
            kit_id="my-kit",
            hook_definitions=hooks,
            source_dir=source_dir,
        )

        assert set(installed_ids) == {"validator", "formatter"}

        settings = load_settings(settings_path)
        assert "PreToolUse" in settings.hooks
        assert "PostToolUse" in settings.hooks

    finally:
        hook_install_module.get_settings_path = original_get_settings
        hook_install_module.get_hooks_dir = original_get_hooks
