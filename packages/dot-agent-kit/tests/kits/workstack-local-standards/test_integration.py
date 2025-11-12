"""Integration tests for workstack-local-standards kit."""

from pathlib import Path

from dot_agent_kit.io import load_kit_manifest


class TestWorkstackLocalStandardsKitIntegration:
    """Integration tests for the complete kit."""

    def test_kit_manifest_loads_successfully(self) -> None:
        """Test that the kit manifest can be loaded without errors."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )

        manifest = load_kit_manifest(manifest_path)

        assert manifest is not None
        assert manifest.name == "workstack-local-standards"

    def test_kit_has_expected_artifacts(self) -> None:
        """Test that kit manifest includes all expected artifacts."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )

        manifest = load_kit_manifest(manifest_path)

        # Should have skill artifact
        assert "skill" in manifest.artifacts
        assert len(manifest.artifacts["skill"]) > 0

    def test_kit_has_cli_commands(self) -> None:
        """Test that kit manifest includes CLI commands."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )

        manifest = load_kit_manifest(manifest_path)

        assert len(manifest.kit_cli_commands) > 0
        command_names = [cmd.name for cmd in manifest.kit_cli_commands]
        assert "local-standards-reminder-hook" in command_names

    def test_kit_has_hooks(self) -> None:
        """Test that kit manifest includes hook definitions."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )

        manifest = load_kit_manifest(manifest_path)

        assert manifest.hooks is not None
        assert len(manifest.hooks) > 0

        hook_ids = [hook.id for hook in manifest.hooks]
        assert "local-standards-reminder-hook" in hook_ids

    def test_command_file_is_importable(self) -> None:
        """Test that the command file can be imported without errors."""
        # This tests that there are no syntax errors or import issues
        import importlib.util

        module_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit_cli_commands"
            / "workstack-local-standards"
            / "local_standards_reminder_hook.py"
        )

        spec = importlib.util.spec_from_file_location("local_standards_reminder_hook", module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {module_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        local_standards_reminder_hook = module.local_standards_reminder_hook

        assert local_standards_reminder_hook is not None
        assert callable(local_standards_reminder_hook)

    def test_skill_file_is_readable(self) -> None:
        """Test that the skill file exists and is readable."""
        skill_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "skills"
            / "workstack-local-standards"
            / "SKILL.md"
        )

        assert skill_path.exists()

        # Should be readable
        content = skill_path.read_text(encoding="utf-8")
        assert len(content) > 0

        # Should contain expected content
        assert "workstack-local-standards" in content.lower()
        assert "kebab-case" in content

    def test_hook_configuration_is_valid(self) -> None:
        """Test that hook configuration has all required fields."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )

        manifest = load_kit_manifest(manifest_path)

        hook = next(h for h in manifest.hooks if h.id == "local-standards-reminder-hook")

        # Verify required hook fields
        assert hook.id is not None
        assert hook.lifecycle is not None
        assert hook.matcher is not None
        assert hook.invocation is not None
        assert hook.timeout is not None

    def test_command_definition_is_valid(self) -> None:
        """Test that CLI command definition has all required fields."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )

        manifest = load_kit_manifest(manifest_path)

        command = next(
            cmd for cmd in manifest.kit_cli_commands if cmd.name == "local-standards-reminder-hook"
        )

        # Verify required command fields
        assert command.name is not None
        assert command.path is not None
        assert command.description is not None

    def test_all_referenced_files_exist(self) -> None:
        """Test that all files referenced in manifest exist."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )

        manifest = load_kit_manifest(manifest_path)
        kit_dir = manifest_path.parent

        # Check skill artifacts
        for skill_path_str in manifest.artifacts.get("skill", []):
            skill_path = kit_dir / skill_path_str
            assert skill_path.exists(), f"Skill file not found: {skill_path}"

        # Check command files
        for command in manifest.kit_cli_commands:
            command_path = kit_dir / command.path
            assert command_path.exists(), f"Command file not found: {command_path}"
