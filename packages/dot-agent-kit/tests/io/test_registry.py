"""Tests for registry operations."""

from pathlib import Path

from dot_agent_kit.io.registry import (
    add_kit_to_registry,
    create_kit_registry_file,
    generate_registry_entry,
    rebuild_registry,
    remove_kit_from_registry,
)
from dot_agent_kit.models import InstalledKit, KitManifest, ProjectConfig


def test_generate_registry_entry() -> None:
    """Test registry entry generation from kit manifest."""
    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit for registry generation",
        artifacts={
            "agent": ["agents/test-agent/test.md"],
            "command": ["commands/test-cmd/test.md"],
            "doc": ["docs/test/reference.md"],
        },
    )

    installed_kit = InstalledKit(
        kit_id="test-kit",
        source_type="bundled",
        version="1.0.0",
        artifacts=[".claude/agents/test-agent/test.md"],
    )

    entry = generate_registry_entry("test-kit", "1.0.0", manifest, installed_kit)

    # Verify required fields present
    assert "### test-kit (v1.0.0)" in entry
    assert "**Purpose**: Test kit for registry generation" in entry
    assert "**Usage**:" in entry

    # Verify artifacts listed
    assert "agent: agents/test-agent/test.md" in entry
    assert "command: commands/test-cmd/test.md" in entry

    # Verify usage examples generated
    assert 'Use Task tool with subagent_type="test-agent"' in entry
    assert "Run `/test-cmd` command" in entry


def test_generate_registry_entry_minimal() -> None:
    """Test registry entry with minimal artifacts (doc only)."""
    manifest = KitManifest(
        name="doc-kit",
        version="1.0.0",
        description="Documentation only kit",
        artifacts={
            "doc": ["docs/reference.md"],
        },
    )

    installed_kit = InstalledKit(
        kit_id="doc-kit",
        source_type="bundled",
        version="1.0.0",
        artifacts=[".claude/docs/reference.md"],
    )

    entry = generate_registry_entry("doc-kit", "1.0.0", manifest, installed_kit)

    # Should have fallback usage text
    assert "Reference documentation loaded automatically" in entry


def test_create_kit_registry_file(tmp_path: Path) -> None:
    """Test creating registry entry file."""
    entry_content = "### test-kit (v1.0.0)\n\n**Purpose**: Test\n\n**Usage**: Test usage\n"

    result_path = create_kit_registry_file("test-kit", entry_content, tmp_path)

    # Verify file created
    assert result_path.exists()
    assert result_path == tmp_path / ".agent" / "kits" / "test-kit" / "registry-entry.md"

    # Verify content matches
    assert result_path.read_text(encoding="utf-8") == entry_content


def test_add_kit_to_registry_new_file(tmp_path: Path) -> None:
    """Test adding kit @-include to new registry."""
    add_kit_to_registry("test-kit", tmp_path)

    registry_path = tmp_path / ".claude" / "docs" / "kit-registry.md"

    # Verify registry created
    assert registry_path.exists()

    content = registry_path.read_text(encoding="utf-8")

    # Verify header present
    assert "# Kit Documentation Registry" in content
    assert "AUTO-GENERATED" in content

    # Verify @-include added
    assert "@.agent/kits/test-kit/registry-entry.md" in content


def test_add_kit_to_registry_existing_file(tmp_path: Path) -> None:
    """Test appending kit @-include to existing registry."""
    registry_path = tmp_path / ".claude" / "docs" / "kit-registry.md"
    registry_path.parent.mkdir(parents=True, exist_ok=True)

    # Create existing registry
    registry_path.write_text(
        "# Kit Documentation Registry\n\n@.agent/kits/existing-kit/registry-entry.md\n",
        encoding="utf-8",
    )

    # Add new kit
    add_kit_to_registry("new-kit", tmp_path)

    content = registry_path.read_text(encoding="utf-8")

    # Verify both kits present
    assert "@.agent/kits/existing-kit/registry-entry.md" in content
    assert "@.agent/kits/new-kit/registry-entry.md" in content


def test_add_kit_to_registry_duplicate(tmp_path: Path) -> None:
    """Test adding same kit twice (should be idempotent)."""
    # Add kit once
    add_kit_to_registry("test-kit", tmp_path)

    registry_path = tmp_path / ".claude" / "docs" / "kit-registry.md"
    content_after_first = registry_path.read_text(encoding="utf-8")

    # Add same kit again
    add_kit_to_registry("test-kit", tmp_path)

    content_after_second = registry_path.read_text(encoding="utf-8")

    # Content should be unchanged
    assert content_after_first == content_after_second

    # Should only appear once
    assert content_after_second.count("@.agent/kits/test-kit/registry-entry.md") == 1


def test_remove_kit_from_registry(tmp_path: Path) -> None:
    """Test removing kit from registry."""
    # Create registry with kit
    registry_path = tmp_path / ".claude" / "docs" / "kit-registry.md"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        "# Kit Documentation Registry\n\n"
        "@.agent/kits/kit1/registry-entry.md\n\n"
        "@.agent/kits/kit2/registry-entry.md\n\n"
        "@.agent/kits/kit3/registry-entry.md\n",
        encoding="utf-8",
    )

    # Create kit registry directory
    kit_dir = tmp_path / ".agent" / "kits" / "kit2"
    kit_dir.mkdir(parents=True, exist_ok=True)
    (kit_dir / "registry-entry.md").write_text("content", encoding="utf-8")

    # Remove kit2
    remove_kit_from_registry("kit2", tmp_path)

    content = registry_path.read_text(encoding="utf-8")

    # Verify kit2 removed
    assert "@.agent/kits/kit2/registry-entry.md" not in content

    # Verify other kits still present
    assert "@.agent/kits/kit1/registry-entry.md" in content
    assert "@.agent/kits/kit3/registry-entry.md" in content

    # Verify directory deleted
    assert not kit_dir.exists()


def test_remove_kit_from_registry_nonexistent(tmp_path: Path) -> None:
    """Test removing nonexistent kit (should not error)."""
    # Create empty registry
    registry_path = tmp_path / ".claude" / "docs" / "kit-registry.md"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text("# Kit Documentation Registry\n\n", encoding="utf-8")

    # Should not raise
    remove_kit_from_registry("nonexistent-kit", tmp_path)


def test_rebuild_registry(tmp_path: Path) -> None:
    """Test rebuilding entire registry from installed kits."""
    # Note: This test requires actual kit manifests to be resolvable
    # For now, we test with empty config (no kits installed)

    config = ProjectConfig(version="1", kits={})

    rebuild_registry(tmp_path, config)

    registry_path = tmp_path / ".claude" / "docs" / "kit-registry.md"

    # Verify registry created
    assert registry_path.exists()

    content = registry_path.read_text(encoding="utf-8")

    # Verify header present
    assert "# Kit Documentation Registry" in content
    assert "AUTO-GENERATED" in content


def test_generate_registry_entry_with_skill() -> None:
    """Test registry entry with skill artifact."""
    manifest = KitManifest(
        name="skill-kit",
        version="1.0.0",
        description="Kit with skill",
        artifacts={
            "skill": ["skills/test-skill/SKILL.md"],
        },
    )

    installed_kit = InstalledKit(
        kit_id="skill-kit",
        source_type="bundled",
        version="1.0.0",
        artifacts=[".claude/skills/test-skill/SKILL.md"],
    )

    entry = generate_registry_entry("skill-kit", "1.0.0", manifest, installed_kit)

    # Verify skill usage example
    assert "Load `test-skill` skill" in entry
