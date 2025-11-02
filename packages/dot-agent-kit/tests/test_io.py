"""Tests for I/O operations."""

from pathlib import Path

from dot_agent_kit.io import (
    add_frontmatter,
    create_default_config,
    load_kit_manifest,
    load_project_config,
    load_registry,
    parse_frontmatter,
    save_project_config,
)
from dot_agent_kit.models import ArtifactFrontmatter, InstalledKit


def test_load_save_project_config(tmp_project: Path) -> None:
    """Test round-trip TOML read/write."""
    config = create_default_config()

    # Add a kit
    kit = InstalledKit(
        kit_id="test-kit",
        version="1.0.0",
        source="test-source",
        installed_at="2025-01-01T00:00:00",
        artifacts=["artifact1.md"],
    )

    from dot_agent_kit.models import ProjectConfig

    config = ProjectConfig(
        version="1",
        default_conflict_policy="error",
        kits={"test-kit": kit},
    )

    # Save and load
    save_project_config(tmp_project, config)
    loaded_config = load_project_config(tmp_project)

    assert loaded_config is not None
    assert loaded_config.version == "1"
    assert loaded_config.default_conflict_policy == "error"
    assert "test-kit" in loaded_config.kits
    assert loaded_config.kits["test-kit"].kit_id == "test-kit"
    assert loaded_config.kits["test-kit"].version == "1.0.0"


def test_load_nonexistent_config(tmp_project: Path) -> None:
    """Test loading returns None when file doesn't exist."""
    config = load_project_config(tmp_project)
    assert config is None


def test_create_default_config() -> None:
    """Test default config creation."""
    config = create_default_config()

    assert config.version == "1"
    assert config.default_conflict_policy == "error"
    assert len(config.kits) == 0


def test_load_kit_manifest(tmp_path: Path) -> None:
    """Test kit.yaml parsing."""
    manifest_path = tmp_path / "kit.yaml"
    manifest_path.write_text(
        "name: test-kit\n"
        "version: 1.0.0\n"
        "description: Test kit\n"
        "artifacts:\n"
        "  agent:\n"
        "    - agents/test.md\n"
        "license: MIT\n"
        "homepage: https://example.com\n",
        encoding="utf-8",
    )

    manifest = load_kit_manifest(manifest_path)

    assert manifest.name == "test-kit"
    assert manifest.version == "1.0.0"
    assert manifest.description == "Test kit"
    assert manifest.artifacts == {"agent": ["agents/test.md"]}
    assert manifest.license == "MIT"
    assert manifest.homepage == "https://example.com"


def test_load_kit_manifest_minimal(tmp_path: Path) -> None:
    """Test kit.yaml with minimal fields."""
    manifest_path = tmp_path / "kit.yaml"
    manifest_path.write_text(
        "name: test-kit\nversion: 1.0.0\ndescription: Test kit\n",
        encoding="utf-8",
    )

    manifest = load_kit_manifest(manifest_path)

    assert manifest.name == "test-kit"
    assert manifest.version == "1.0.0"
    assert manifest.description == "Test kit"
    assert manifest.artifacts == {}
    assert manifest.license is None
    assert manifest.homepage is None


def test_parse_frontmatter() -> None:
    """Test extracting frontmatter from markdown."""
    content = """<!-- dot-agent-kit:
kit_id: test-kit
kit_version: 1.0.0
artifact_type: agent
artifact_path: agents/test.md
-->

# Test Agent

This is the agent content.
"""

    frontmatter = parse_frontmatter(content)

    assert frontmatter is not None
    assert frontmatter.kit_id == "test-kit"
    assert frontmatter.kit_version == "1.0.0"
    assert frontmatter.artifact_type == "agent"
    assert frontmatter.artifact_path == "agents/test.md"


def test_parse_frontmatter_none() -> None:
    """Test parsing content without frontmatter."""
    content = "# Test Agent\n\nNo frontmatter here."

    frontmatter = parse_frontmatter(content)

    assert frontmatter is None


def test_add_frontmatter() -> None:
    """Test injecting frontmatter into markdown."""
    content = "# Test Agent\n\nAgent content."

    frontmatter = ArtifactFrontmatter(
        kit_id="test-kit",
        kit_version="1.0.0",
        artifact_type="agent",
        artifact_path="agents/test.md",
    )

    result = add_frontmatter(content, frontmatter)

    assert "<!-- dot-agent-kit:" in result
    assert "kit_id: test-kit" in result
    assert "kit_version: 1.0.0" in result
    assert "artifact_type: agent" in result
    assert "artifact_path: agents/test.md" in result
    assert "# Test Agent" in result
    assert "Agent content." in result


def test_add_frontmatter_roundtrip() -> None:
    """Test frontmatter can be added and parsed back."""
    original_content = "# Test Agent\n\nAgent content."

    frontmatter_obj = ArtifactFrontmatter(
        kit_id="test-kit",
        kit_version="1.0.0",
        artifact_type="agent",
        artifact_path="agents/test.md",
    )

    content_with_fm = add_frontmatter(original_content, frontmatter_obj)
    parsed_fm = parse_frontmatter(content_with_fm)

    assert parsed_fm is not None
    assert parsed_fm.kit_id == frontmatter_obj.kit_id
    assert parsed_fm.kit_version == frontmatter_obj.kit_version
    assert parsed_fm.artifact_type == frontmatter_obj.artifact_type
    assert parsed_fm.artifact_path == frontmatter_obj.artifact_path


def test_load_registry() -> None:
    """Test loading registry with entries."""
    registry = load_registry()

    assert isinstance(registry, list)
    assert len(registry) >= 1  # Should have at least dev-runners-da-kit
    assert any(entry.kit_id == "dev-runners-da-kit" for entry in registry)
