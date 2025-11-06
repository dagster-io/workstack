"""Tests for hook configuration drift detection."""

import json
from pathlib import Path

from click.testing import CliRunner

from dot_agent_kit.commands.check import (
    InstalledHook,
    _detect_hook_drift,
    _extract_hooks_for_kit,
    check,
)
from dot_agent_kit.hooks.models import ClaudeSettings, HookDefinition, HookEntry, MatcherGroup
from dot_agent_kit.io import save_project_config
from dot_agent_kit.models import InstalledKit, ProjectConfig
from dot_agent_kit.sources import BundledKitSource


def test_extract_hooks_for_kit_filters_correctly() -> None:
    """Test that _extract_hooks_for_kit only returns hooks for specified kit."""
    # Create settings with hooks from multiple kits
    settings = ClaudeSettings(
        hooks={
            "UserPromptSubmit": [
                MatcherGroup(
                    matcher="*",
                    hooks=[
                        HookEntry(
                            command=(
                                "DOT_AGENT_KIT_ID=dignified-python "
                                "DOT_AGENT_HOOK_ID=my-hook python3 /path/to/script.py"
                            ),
                            timeout=30,
                        ),
                        HookEntry(
                            command=(
                                "DOT_AGENT_KIT_ID=other-kit "
                                "DOT_AGENT_HOOK_ID=other-hook python3 /path/to/other.py"
                            ),
                            timeout=30,
                        ),
                    ],
                )
            ]
        }
    )

    # Extract hooks for dignified-python
    hooks = _extract_hooks_for_kit(settings, "dignified-python")

    assert len(hooks) == 1
    assert hooks[0].hook_id == "my-hook"
    assert "dignified-python" in hooks[0].command


def test_extract_hooks_for_kit_empty_settings() -> None:
    """Test _extract_hooks_for_kit with empty settings."""
    settings = ClaudeSettings()

    hooks = _extract_hooks_for_kit(settings, "any-kit")

    assert len(hooks) == 0


def test_extract_hooks_for_kit_no_matching_kit() -> None:
    """Test _extract_hooks_for_kit when kit not found."""
    settings = ClaudeSettings(
        hooks={
            "UserPromptSubmit": [
                MatcherGroup(
                    matcher="*",
                    hooks=[
                        HookEntry(
                            command="DOT_AGENT_KIT_ID=other-kit python3 /path/to/script.py",
                            timeout=30,
                        ),
                    ],
                )
            ]
        }
    )

    hooks = _extract_hooks_for_kit(settings, "dignified-python")

    assert len(hooks) == 0


def test_detect_hook_drift_no_drift() -> None:
    """Test _detect_hook_drift when hooks match expectations."""
    expected_hooks = [
        HookDefinition(
            id="compliance-reminder-hook",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation="dot-agent run dignified-python compliance-reminder-hook",
            description="Test hook",
            timeout=30,
        )
    ]

    installed_hooks = [
        InstalledHook(
            hook_id="compliance-reminder-hook",
            command=(
                "DOT_AGENT_KIT_ID=dignified-python "
                "DOT_AGENT_HOOK_ID=compliance-reminder-hook "
                "dot-agent run dignified-python compliance-reminder-hook"
            ),
            timeout=30,
            lifecycle="UserPromptSubmit",
        )
    ]

    result = _detect_hook_drift("dignified-python", expected_hooks, installed_hooks)

    assert result is None


def test_detect_hook_drift_missing_hook() -> None:
    """Test _detect_hook_drift detects missing hook."""
    expected_hooks = [
        HookDefinition(
            id="compliance-reminder-hook",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation="dot-agent run dignified-python compliance-reminder-hook",
            description="Test hook",
            timeout=30,
        )
    ]

    installed_hooks: list[InstalledHook] = []

    result = _detect_hook_drift("dignified-python", expected_hooks, installed_hooks)

    assert result is not None
    assert len(result.issues) == 1
    assert result.issues[0].severity == "error"
    assert "Missing hook" in result.issues[0].message
    assert result.issues[0].expected == "compliance-reminder-hook"


def test_detect_hook_drift_outdated_command_format() -> None:
    """Test _detect_hook_drift detects outdated command format."""
    expected_hooks = [
        HookDefinition(
            id="compliance-reminder-hook",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation="dot-agent run dignified-python compliance-reminder-hook",
            description="Test hook",
            timeout=30,
        )
    ]

    installed_hooks = [
        InstalledHook(
            hook_id="compliance-reminder-hook",
            command="DOT_AGENT_KIT_ID=dignified-python python3 /path/to/script.py",
            timeout=30,
            lifecycle="UserPromptSubmit",
        )
    ]

    result = _detect_hook_drift("dignified-python", expected_hooks, installed_hooks)

    assert result is not None
    assert len(result.issues) == 1
    assert result.issues[0].severity == "warning"
    assert "Command mismatch" in result.issues[0].message


def test_detect_hook_drift_obsolete_hook() -> None:
    """Test _detect_hook_drift detects obsolete hook."""
    expected_hooks: list[HookDefinition] = []

    installed_hooks = [
        InstalledHook(
            hook_id="old-hook",
            command="DOT_AGENT_KIT_ID=dignified-python python3 /path/to/old.py",
            timeout=30,
            lifecycle="UserPromptSubmit",
        )
    ]

    result = _detect_hook_drift("dignified-python", expected_hooks, installed_hooks)

    assert result is not None
    assert len(result.issues) == 1
    assert result.issues[0].severity == "warning"
    assert "Obsolete hook" in result.issues[0].message


def test_detect_hook_drift_hook_id_mismatch() -> None:
    """Test _detect_hook_drift detects hook ID mismatch (old vs new ID)."""
    expected_hooks = [
        HookDefinition(
            id="compliance-reminder-hook",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation="dot-agent run dignified-python compliance-reminder-hook",
            description="Test hook",
            timeout=30,
        )
    ]

    # Installed hook has old ID
    installed_hooks = [
        InstalledHook(
            hook_id="suggest-dignified-python",
            command="DOT_AGENT_KIT_ID=dignified-python python3 /path/to/script.py",
            timeout=30,
            lifecycle="UserPromptSubmit",
        )
    ]

    result = _detect_hook_drift("dignified-python", expected_hooks, installed_hooks)

    assert result is not None
    # Should detect missing (new ID) and obsolete (old ID)
    assert len(result.issues) == 2
    assert any("Missing hook" in issue.message for issue in result.issues)
    assert any("Obsolete hook" in issue.message for issue in result.issues)


def test_detect_hook_drift_multiple_issues() -> None:
    """Test _detect_hook_drift with multiple drift issues."""
    expected_hooks = [
        HookDefinition(
            id="hook-1",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation="dot-agent run test-kit hook-1",
            description="Hook 1",
            timeout=30,
        ),
        HookDefinition(
            id="hook-2",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation="dot-agent run test-kit hook-2",
            description="Hook 2",
            timeout=30,
        ),
    ]

    installed_hooks = [
        InstalledHook(
            hook_id="hook-1",
            command="DOT_AGENT_KIT_ID=test-kit python3 /path/to/hook1.py",
            timeout=30,
            lifecycle="UserPromptSubmit",
        ),
        InstalledHook(
            hook_id="old-hook",
            command="DOT_AGENT_KIT_ID=test-kit python3 /path/to/old.py",
            timeout=30,
            lifecycle="UserPromptSubmit",
        ),
    ]

    result = _detect_hook_drift("test-kit", expected_hooks, installed_hooks)

    assert result is not None
    # Missing hook-2, outdated format for hook-1, obsolete old-hook
    assert len(result.issues) == 3


def test_check_command_no_hook_drift(tmp_path: Path) -> None:
    """Test check command when no hook drift detected."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create .claude directory
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Create settings.json with no hooks
        settings_path = claude_dir / "settings.json"
        settings_path.write_text("{}", encoding="utf-8")

        # Create kit.yaml artifact file
        kit_yaml_path = claude_dir / "kit.yaml"
        kit_yaml_path.write_text("name: test-kit\nversion: 1.0.0\n", encoding="utf-8")

        # Create config with bundled kit
        config = ProjectConfig(
            version="1",
            kits={
                "test-kit": InstalledKit(
                    kit_id="test-kit",
                    version="1.0.0",
                    source_type="bundled",
                    installed_at="2024-01-01T00:00:00",
                    artifacts=[".claude/kit.yaml"],
                ),
            },
        )
        save_project_config(project_dir, config)

        result = runner.invoke(check)

        assert result.exit_code == 0
        assert "Hook Configuration Validation" in result.output
        assert "No hook drift detected" in result.output


def test_check_command_skip_non_bundled_kits(tmp_path: Path) -> None:
    """Test check command skips non-bundled kits for hook validation."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create .claude directory
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Create settings.json with hook for non-bundled kit
        settings_data = {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "command": (
                                    "DOT_AGENT_KIT_ID=package-kit python3 /path/to/script.py"
                                ),
                                "timeout": 30,
                            }
                        ],
                    }
                ]
            }
        }
        settings_path = claude_dir / "settings.json"
        settings_path.write_text(json.dumps(settings_data), encoding="utf-8")

        # Create kit.yaml artifact file
        kit_yaml_path = claude_dir / "kit.yaml"
        kit_yaml_path.write_text("name: package-kit\nversion: 1.0.0\n", encoding="utf-8")

        # Create config with package kit (not bundled)
        config = ProjectConfig(
            version="1",
            kits={
                "package-kit": InstalledKit(
                    kit_id="package-kit",
                    version="1.0.0",
                    source_type="package",
                    installed_at="2024-01-01T00:00:00",
                    artifacts=[".claude/kit.yaml"],
                ),
            },
        )
        save_project_config(project_dir, config)

        result = runner.invoke(check)

        # Should pass - non-bundled kits are skipped
        assert result.exit_code == 0
        assert "No hook drift detected" in result.output


def test_check_command_skip_kit_without_hooks_field(tmp_path: Path) -> None:
    """Test check command skips kits with no hooks field in manifest."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create .claude directory
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Create settings.json
        settings_path = claude_dir / "settings.json"
        settings_path.write_text("{}", encoding="utf-8")

        # Create a mock bundled kit without hooks field
        mock_kit_dir = tmp_path / "mock_bundled_kit"
        mock_kit_dir.mkdir()

        manifest_content = """name: test-kit
version: 1.0.0
description: Test kit
artifacts:
  command:
  - kit.yaml
"""

        manifest_path = mock_kit_dir / "kit.yaml"
        manifest_path.write_text(manifest_content, encoding="utf-8")

        # Create kit.yaml artifact file (must match manifest for sync check to pass)
        kit_yaml_path = claude_dir / "kit.yaml"
        kit_yaml_path.write_text(manifest_content, encoding="utf-8")

        # Create config
        config = ProjectConfig(
            version="1",
            kits={
                "test-kit": InstalledKit(
                    kit_id="test-kit",
                    version="1.0.0",
                    source_type="bundled",
                    installed_at="2024-01-01T00:00:00",
                    artifacts=[".claude/kit.yaml"],
                ),
            },
        )
        save_project_config(project_dir, config)

        # Monkey patch BundledKitSource
        original_get_path = BundledKitSource._get_bundled_kit_path

        def mock_get_path(self: BundledKitSource, source: str) -> Path | None:
            if source == "test-kit":
                return mock_kit_dir
            return original_get_path(self, source)

        BundledKitSource._get_bundled_kit_path = mock_get_path

        result = runner.invoke(check)

        # Restore original method
        BundledKitSource._get_bundled_kit_path = original_get_path

        # Should pass - kits without hooks field are skipped
        assert result.exit_code == 0
        assert "No hook drift detected" in result.output


def test_check_command_detects_hook_drift_integration(tmp_path: Path) -> None:
    """Integration test: check command detects actual hook drift."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create .claude directory
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Create settings.json with old hook reference
        settings_data = {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "command": (
                                    "DOT_AGENT_KIT_ID=test-kit "
                                    "DOT_AGENT_HOOK_ID=old-hook python3 /path/to/old_hook.py"
                                ),
                                "timeout": 30,
                            }
                        ],
                    }
                ]
            }
        }
        settings_path = claude_dir / "settings.json"
        settings_path.write_text(json.dumps(settings_data), encoding="utf-8")

        # Create a mock bundled kit with hooks field
        mock_kit_dir = tmp_path / "mock_bundled_kit"
        mock_kit_dir.mkdir()

        manifest_path = mock_kit_dir / "kit.yaml"
        manifest_path.write_text(
            """name: test-kit
version: 1.0.0
description: Test kit
artifacts: {}
hooks:
  - id: new-hook
    lifecycle: UserPromptSubmit
    matcher: "*"
    invocation: dot-agent run test-kit new-hook
    description: New hook
    timeout: 30
""",
            encoding="utf-8",
        )

        # Create config
        config = ProjectConfig(
            version="1",
            kits={
                "test-kit": InstalledKit(
                    kit_id="test-kit",
                    version="1.0.0",
                    source_type="bundled",
                    installed_at="2024-01-01T00:00:00",
                    artifacts=[],
                ),
            },
        )
        save_project_config(project_dir, config)

        # Monkey patch BundledKitSource
        original_get_path = BundledKitSource._get_bundled_kit_path

        def mock_get_path(self: BundledKitSource, source: str) -> Path | None:
            if source == "test-kit":
                return mock_kit_dir
            return original_get_path(self, source)

        BundledKitSource._get_bundled_kit_path = mock_get_path

        result = runner.invoke(check)

        # Restore original method
        BundledKitSource._get_bundled_kit_path = original_get_path

        # Should detect drift
        assert result.exit_code == 1
        assert "Hook Configuration Validation" in result.output
        assert "Kit: test-kit" in result.output
        assert "Missing hook" in result.output or "Obsolete hook" in result.output
        assert "Some checks failed" in result.output


def test_check_command_no_settings_file(tmp_path: Path) -> None:
    """Test check command when settings.json doesn't exist."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create .claude directory but no settings.json
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Create kit.yaml artifact file
        kit_yaml_path = claude_dir / "kit.yaml"
        kit_yaml_path.write_text("name: test-kit\nversion: 1.0.0\n", encoding="utf-8")

        # Create config with bundled kit
        config = ProjectConfig(
            version="1",
            kits={
                "test-kit": InstalledKit(
                    kit_id="test-kit",
                    version="1.0.0",
                    source_type="bundled",
                    installed_at="2024-01-01T00:00:00",
                    artifacts=[".claude/kit.yaml"],
                ),
            },
        )
        save_project_config(project_dir, config)

        result = runner.invoke(check)

        # Should pass - no settings.json means no hooks to validate
        assert result.exit_code == 0
        assert "No hook drift detected" in result.output
