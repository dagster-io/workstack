"""Tests for kit installation."""

from pathlib import Path

import pytest

from dot_agent_kit.operations.install import install_kit
from dot_agent_kit.sources import ResolvedKit


def test_install_kit_basic(tmp_project: Path) -> None:
    """Test basic kit installation."""
    # Create mock kit
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: test-kit\n"
        "version: 1.0.0\n"
        "description: Test\n"
        "artifacts:\n"
        "  agent:\n"
        "    - agents/test-agent.md\n",
        encoding="utf-8",
    )

    agents_dir = kit_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "test-agent.md").write_text("# Test Agent", encoding="utf-8")

    # Mock resolution
    resolved = ResolvedKit(
        kit_id="test-kit",
        source_type="package",
        source="test-kit",
        manifest_path=manifest,
        artifacts_base=kit_dir,
    )

    # Install
    installed = install_kit(resolved, tmp_project)

    # Verify
    assert installed.kit_id == "test-kit"
    assert installed.version == "1.0.0"
    assert len(installed.artifacts) == 1

    agent_path = tmp_project / ".claude" / "agents" / "test-agent.md"
    assert agent_path.exists()

    content = agent_path.read_text(encoding="utf-8")
    assert "# Test Agent" in content


def test_install_kit_conflict(tmp_project: Path) -> None:
    """Test installation fails on conflict with ERROR policy."""
    # Create existing artifact
    claude_dir = tmp_project / ".claude"
    claude_dir.mkdir()
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "test-agent.md").write_text("Existing", encoding="utf-8")

    # Create mock kit
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: test-kit\n"
        "version: 1.0.0\n"
        "description: Test\n"
        "artifacts:\n"
        "  agent:\n"
        "    - agents/test-agent.md\n",
        encoding="utf-8",
    )

    agents_source = kit_dir / "agents"
    agents_source.mkdir()
    (agents_source / "test-agent.md").write_text("# New Agent", encoding="utf-8")

    resolved = ResolvedKit(
        kit_id="test-kit",
        source_type="package",
        source="test-kit",
        manifest_path=manifest,
        artifacts_base=kit_dir,
    )

    # Try to install - should fail with default (overwrite=False)
    with pytest.raises(FileExistsError, match="Artifact already exists"):
        install_kit(resolved, tmp_project, overwrite=False)


def test_install_kit_creates_directories(tmp_project: Path) -> None:
    """Test installation creates .claude directory structure."""
    # Create mock kit
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: test-kit\n"
        "version: 1.0.0\n"
        "description: Test\n"
        "artifacts:\n"
        "  command:\n"
        "    - commands/test-command.md\n",
        encoding="utf-8",
    )

    commands_dir = kit_dir / "commands"
    commands_dir.mkdir()
    (commands_dir / "test-command.md").write_text("# Test Command", encoding="utf-8")

    resolved = ResolvedKit(
        kit_id="test-kit",
        source_type="package",
        source="test-kit",
        manifest_path=manifest,
        artifacts_base=kit_dir,
    )

    # Install
    install_kit(resolved, tmp_project)

    # Verify directories created
    assert (tmp_project / ".claude").exists()
    assert (tmp_project / ".claude" / "commands").exists()
    assert (tmp_project / ".claude" / "commands" / "test-command.md").exists()


def test_install_kit_overwrite_policy(tmp_project: Path) -> None:
    """Test overwrite=True replaces existing files."""
    # Create existing artifact
    claude_dir = tmp_project / ".claude/agents"
    claude_dir.mkdir(parents=True)
    existing = claude_dir / "test-agent.md"
    existing.write_text("Original content", encoding="utf-8")

    # Create mock kit
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: test-kit\n"
        "version: 1.0.0\n"
        "description: Test\n"
        "artifacts:\n"
        "  agent:\n"
        "    - agents/test-agent.md\n",
        encoding="utf-8",
    )

    agents_source = kit_dir / "agents"
    agents_source.mkdir()
    (agents_source / "test-agent.md").write_text("# New Agent", encoding="utf-8")

    resolved = ResolvedKit(
        kit_id="test-kit",
        source_type="package",
        source="test-kit",
        manifest_path=manifest,
        artifacts_base=kit_dir,
    )

    # Install with overwrite=True
    installed = install_kit(resolved, tmp_project, overwrite=True)

    # Verify new content written
    content = existing.read_text(encoding="utf-8")
    assert "# New Agent" in content
    assert len(installed.artifacts) == 1


def test_install_kit_namespaced_artifacts(tmp_project: Path) -> None:
    """Test installation of namespaced kit artifacts."""
    # Create mock kit with namespaced structure
    kit_dir = tmp_project / "mock_kit"
    kit_dir.mkdir()

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: my-kit\n"
        "version: 1.0.0\n"
        "description: Namespaced kit\n"
        "artifacts:\n"
        "  agent:\n"
        "    - agents/my-kit/helper.md\n"
        "  skill:\n"
        "    - skills/my-kit/tool-a/SKILL.md\n"
        "    - skills/my-kit/tool-b/SKILL.md\n"
        "  command:\n"
        "    - commands/my-kit/build.md\n",
        encoding="utf-8",
    )

    # Create namespaced agent
    agents_dir = kit_dir / "agents" / "my-kit"
    agents_dir.mkdir(parents=True)
    (agents_dir / "helper.md").write_text("# Helper Agent", encoding="utf-8")

    # Create namespaced skills
    skill_a_dir = kit_dir / "skills" / "my-kit" / "tool-a"
    skill_a_dir.mkdir(parents=True)
    (skill_a_dir / "SKILL.md").write_text("# Tool A Skill", encoding="utf-8")

    skill_b_dir = kit_dir / "skills" / "my-kit" / "tool-b"
    skill_b_dir.mkdir(parents=True)
    (skill_b_dir / "SKILL.md").write_text("# Tool B Skill", encoding="utf-8")

    # Create namespaced command
    commands_dir = kit_dir / "commands" / "my-kit"
    commands_dir.mkdir(parents=True)
    (commands_dir / "build.md").write_text("# Build Command", encoding="utf-8")

    # Mock resolution
    resolved = ResolvedKit(
        kit_id="my-kit",
        source_type="bundled",
        source="my-kit",
        manifest_path=manifest,
        artifacts_base=kit_dir,
    )

    # Install
    installed = install_kit(resolved, tmp_project)

    # Verify namespaced structure is preserved in .claude/
    claude_dir = tmp_project / ".claude"

    # Check agent namespace
    agent_path = claude_dir / "agents" / "my-kit" / "helper.md"
    assert agent_path.exists()
    assert "# Helper Agent" in agent_path.read_text(encoding="utf-8")

    # Check skill namespaces
    skill_a_path = claude_dir / "skills" / "my-kit" / "tool-a" / "SKILL.md"
    assert skill_a_path.exists()
    assert "# Tool A Skill" in skill_a_path.read_text(encoding="utf-8")

    skill_b_path = claude_dir / "skills" / "my-kit" / "tool-b" / "SKILL.md"
    assert skill_b_path.exists()
    assert "# Tool B Skill" in skill_b_path.read_text(encoding="utf-8")

    # Check command namespace
    command_path = claude_dir / "commands" / "my-kit" / "build.md"
    assert command_path.exists()
    assert "# Build Command" in command_path.read_text(encoding="utf-8")

    # Verify all artifacts were installed
    assert len(installed.artifacts) == 4

    # Verify artifact content
    agent_content = agent_path.read_text(encoding="utf-8")
    assert "# Helper Agent" in agent_content

    skill_a_content = skill_a_path.read_text(encoding="utf-8")
    assert "# Tool A Skill" in skill_a_content


def test_kit_manifest_namespace_validation() -> None:
    """Test KitManifest namespace validation (informational only, not enforced)."""
    from dot_agent_kit.models.kit import KitManifest

    # Namespace validation is not enforced - all structures are allowed
    manifest = KitManifest(
        name="my-kit",
        version="1.0.0",
        description="Test",
        artifacts={
            "agent": ["agents/helper.md"],  # Any structure allowed
            "skill": ["skills/wrong-namespace/tool/SKILL.md"],  # Any structure allowed
        },
    )
    errors = manifest.validate_namespace_pattern()
    assert errors == []  # No enforcement - returns empty list


def test_bundled_kit_namespace_enforcement(tmp_path: Path) -> None:
    """Test that bundled kits can use any namespace structure (not enforced)."""
    from dot_agent_kit.sources.bundled import BundledKitSource

    # Create a mock bundled kit with any namespace structure
    kit_dir = tmp_path / "data" / "kits" / "any-kit"
    kit_dir.mkdir(parents=True)

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: any-kit\n"
        "version: 1.0.0\n"
        "description: Kit with any namespace structure\n"
        "artifacts:\n"
        "  agent:\n"
        "    - agents/helper.md\n",  # Any structure is allowed
        encoding="utf-8",
    )

    agents_dir = kit_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "helper.md").write_text("# Helper Agent", encoding="utf-8")

    # Create a custom source that points to our temp directory
    class TestBundledSource(BundledKitSource):
        def _get_bundled_kit_path(self, source: str) -> Path | None:
            test_path = tmp_path / "data" / "kits" / source
            if test_path.exists():
                return test_path
            return None

    source = TestBundledSource()

    # Should resolve successfully - namespace validation is not enforced
    resolved = source.resolve("any-kit")
    assert resolved.kit_id == "any-kit"


def test_bundled_kit_valid_namespace_succeeds(tmp_path: Path) -> None:
    """Test that properly namespaced bundled kits resolve successfully."""
    from dot_agent_kit.sources.bundled import BundledKitSource

    # Create a mock bundled kit with valid namespace
    kit_dir = tmp_path / "data" / "kits" / "good-kit"
    kit_dir.mkdir(parents=True)

    manifest = kit_dir / "kit.yaml"
    manifest.write_text(
        "name: good-kit\n"
        "version: 1.0.0\n"
        "description: Kit with valid namespace\n"
        "artifacts:\n"
        "  agent:\n"
        "    - agents/good-kit/helper.md\n",  # Properly namespaced
        encoding="utf-8",
    )

    agents_dir = kit_dir / "agents" / "good-kit"
    agents_dir.mkdir(parents=True)
    (agents_dir / "helper.md").write_text("# Helper Agent", encoding="utf-8")

    # Create a custom source that points to our temp directory
    class TestBundledSource(BundledKitSource):
        def _get_bundled_kit_path(self, source: str) -> Path | None:
            test_path = tmp_path / "data" / "kits" / source
            if test_path.exists():
                return test_path
            return None

    source = TestBundledSource()

    # Should resolve successfully
    resolved = source.resolve("good-kit")
    assert resolved.kit_id == "good-kit"
