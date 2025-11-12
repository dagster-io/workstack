"""Tests for workstack-local-standards kit manifest validation."""

from pathlib import Path

import yaml


class TestKitManifest:
    """Tests for the kit.yaml manifest file."""

    def test_manifest_file_exists(self) -> None:
        """Test that kit.yaml exists in the expected location."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )
        assert manifest_path.exists(), f"Manifest not found at {manifest_path}"

    def test_manifest_is_valid_yaml(self) -> None:
        """Test that kit.yaml is valid YAML."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )

        with manifest_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data is not None
        assert isinstance(data, dict)

    def test_manifest_has_required_fields(self) -> None:
        """Test that manifest has all required fields."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )

        with manifest_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Required fields
        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert "license" in data

    def test_manifest_name_matches_expected(self) -> None:
        """Test that kit name is correct."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )

        with manifest_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data["name"] == "workstack-local-standards"

    def test_manifest_has_skill_artifact(self) -> None:
        """Test that manifest defines skill artifact."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )

        with manifest_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert "artifacts" in data
        assert "skill" in data["artifacts"]
        assert len(data["artifacts"]["skill"]) > 0

    def test_manifest_has_kit_cli_commands(self) -> None:
        """Test that manifest defines kit CLI commands."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )

        with manifest_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert "kit_cli_commands" in data
        assert len(data["kit_cli_commands"]) > 0

    def test_local_standards_reminder_hook_command_defined(self) -> None:
        """Test that local-standards-reminder-hook command is defined."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )

        with manifest_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        commands = data["kit_cli_commands"]
        command_names = [cmd["name"] for cmd in commands]

        assert "local-standards-reminder-hook" in command_names

    def test_command_has_required_fields(self) -> None:
        """Test that command definition has required fields."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )

        with manifest_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        commands = data["kit_cli_commands"]
        hook_command = next(
            cmd for cmd in commands if cmd["name"] == "local-standards-reminder-hook"
        )

        assert "name" in hook_command
        assert "path" in hook_command
        assert "description" in hook_command

    def test_manifest_has_hooks(self) -> None:
        """Test that manifest defines hooks."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )

        with manifest_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert "hooks" in data
        assert len(data["hooks"]) > 0

    def test_hook_configuration(self) -> None:
        """Test the hook configuration details."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )

        with manifest_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        hooks = data["hooks"]
        hook = next(hook for hook in hooks if hook["id"] == "local-standards-reminder-hook")

        # Verify hook configuration
        assert hook["lifecycle"] == "UserPromptSubmit"
        assert hook["matcher"] == "*.py"
        assert "dot-agent run workstack-local-standards local-standards-reminder-hook" in hook["invocation"]
        assert hook["timeout"] == 30

    def test_hook_has_description(self) -> None:
        """Test that hook has a description."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )

        with manifest_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        hooks = data["hooks"]
        hook = next(hook for hook in hooks if hook["id"] == "local-standards-reminder-hook")

        assert "description" in hook
        assert len(hook["description"]) > 0

    def test_skill_file_exists(self) -> None:
        """Test that the referenced skill file exists."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )

        with manifest_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        skill_paths = data["artifacts"]["skill"]
        kit_dir = manifest_path.parent

        for skill_path in skill_paths:
            full_path = kit_dir / skill_path
            assert full_path.exists(), f"Skill file not found: {full_path}"

    def test_command_file_exists(self) -> None:
        """Test that the referenced command file exists."""
        manifest_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / "workstack-local-standards"
            / "kit.yaml"
        )

        with manifest_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        commands = data["kit_cli_commands"]
        kit_dir = manifest_path.parent

        for command in commands:
            command_path = kit_dir / command["path"]
            assert command_path.exists(), f"Command file not found: {command_path}"
