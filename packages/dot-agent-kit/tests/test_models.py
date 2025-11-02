"""Tests for data models."""

import pytest

from dot_agent_kit.models import (
    ArtifactFrontmatter,
    ConflictPolicy,
    InstalledKit,
    KitManifest,
    ProjectConfig,
    RegistryEntry,
)


def test_conflict_policy_literals() -> None:
    """Test ConflictPolicy literal type values."""
    # ConflictPolicy is now a Literal type, test that string values work
    policy: ConflictPolicy = "error"
    assert policy == "error"

    policy = "skip"
    assert policy == "skip"

    policy = "overwrite"
    assert policy == "overwrite"

    policy = "merge"
    assert policy == "merge"


def test_installed_kit_immutable() -> None:
    """Test InstalledKit is frozen (immutable)."""
    kit = InstalledKit(
        kit_id="test-kit",
        version="1.0.0",
        source="test-source",
        installed_at="2025-01-01T00:00:00",
        artifacts=["artifact1.md"],
    )

    with pytest.raises(AttributeError):
        kit.version = "2.0.0"  # type: ignore


def test_installed_kit_default_conflict_policy() -> None:
    """Test InstalledKit has default conflict policy."""
    kit = InstalledKit(
        kit_id="test-kit",
        version="1.0.0",
        source="test-source",
        installed_at="2025-01-01T00:00:00",
        artifacts=[],
    )

    assert kit.conflict_policy == "error"


def test_project_config_creation() -> None:
    """Test ProjectConfig model creation."""
    kit = InstalledKit(
        kit_id="test-kit",
        version="1.0.0",
        source="test-source",
        installed_at="2025-01-01T00:00:00",
        artifacts=[],
    )

    config = ProjectConfig(
        version="1",
        default_conflict_policy="error",
        kits={"test-kit": kit},
    )

    assert config.version == "1"
    assert config.default_conflict_policy == "error"
    assert "test-kit" in config.kits
    assert config.kits["test-kit"].kit_id == "test-kit"


def test_project_config_immutable() -> None:
    """Test ProjectConfig is frozen (immutable)."""
    config = ProjectConfig(
        version="1",
        default_conflict_policy="error",
        kits={},
    )

    with pytest.raises(AttributeError):
        config.version = "2"  # type: ignore


def test_kit_manifest_required_fields() -> None:
    """Test KitManifest with required fields only."""
    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={"agent": ["agents/test.md"]},
    )

    assert manifest.name == "test-kit"
    assert manifest.version == "1.0.0"
    assert manifest.description == "Test kit"
    assert manifest.artifacts == {"agent": ["agents/test.md"]}
    assert manifest.license is None
    assert manifest.homepage is None


def test_kit_manifest_with_optional_fields() -> None:
    """Test KitManifest with all fields."""
    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={"agent": ["agents/test.md"]},
        license="MIT",
        homepage="https://example.com",
    )

    assert manifest.license == "MIT"
    assert manifest.homepage == "https://example.com"


def test_kit_manifest_immutable() -> None:
    """Test KitManifest is frozen (immutable)."""
    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit",
        artifacts={},
    )

    with pytest.raises(AttributeError):
        manifest.name = "other-kit"  # type: ignore


def test_artifact_frontmatter() -> None:
    """Test ArtifactFrontmatter model."""
    frontmatter = ArtifactFrontmatter(
        kit_id="test-kit",
        kit_version="1.0.0",
        artifact_type="agent",
        artifact_path="agents/test.md",
    )

    assert frontmatter.kit_id == "test-kit"
    assert frontmatter.kit_version == "1.0.0"
    assert frontmatter.artifact_type == "agent"
    assert frontmatter.artifact_path == "agents/test.md"


def test_artifact_frontmatter_immutable() -> None:
    """Test ArtifactFrontmatter is frozen (immutable)."""
    frontmatter = ArtifactFrontmatter(
        kit_id="test-kit",
        kit_version="1.0.0",
        artifact_type="agent",
        artifact_path="agents/test.md",
    )

    with pytest.raises(AttributeError):
        frontmatter.kit_id = "other-kit"  # type: ignore


def test_registry_entry_required_fields() -> None:
    """Test RegistryEntry with required fields only."""
    entry = RegistryEntry(
        kit_id="test-kit",
        name="Test Kit",
        description="A test kit",
        source="test-kit-package",
    )

    assert entry.kit_id == "test-kit"
    assert entry.name == "Test Kit"
    assert entry.description == "A test kit"
    assert entry.source == "test-kit-package"


def test_registry_entry_immutable() -> None:
    """Test RegistryEntry is frozen (immutable)."""
    entry = RegistryEntry(
        kit_id="test-kit",
        name="Test Kit",
        description="A test kit",
        source="test-kit-package",
    )

    with pytest.raises(AttributeError):
        entry.kit_id = "other-kit"  # type: ignore
