"""Tests for artifact validation."""

from pathlib import Path

from dot_agent_kit.io import validate_frontmatter
from dot_agent_kit.models import ArtifactFrontmatter
from dot_agent_kit.operations import validate_artifact, validate_project


def test_validate_frontmatter_valid() -> None:
    """Test validation of valid frontmatter."""
    fm = ArtifactFrontmatter(
        kit_id="test-kit",
        kit_version="1.0.0",
        artifact_type="agent",
        artifact_path="agents/test.md",
    )

    errors = validate_frontmatter(fm)
    assert len(errors) == 0


def test_validate_frontmatter_invalid_kit_id() -> None:
    """Test validation catches invalid kit_id."""
    fm = ArtifactFrontmatter(
        kit_id="Test_Kit",  # Invalid: uppercase and underscore
        kit_version="1.0.0",
        artifact_type="agent",
        artifact_path="agents/test.md",
    )

    errors = validate_frontmatter(fm)
    assert any("Invalid kit_id format" in e for e in errors)


def test_validate_frontmatter_invalid_version() -> None:
    """Test validation catches invalid version."""
    fm = ArtifactFrontmatter(
        kit_id="test-kit",
        kit_version="v1.0",  # Invalid: doesn't match semver pattern
        artifact_type="agent",
        artifact_path="agents/test.md",
    )

    errors = validate_frontmatter(fm)
    assert any("Invalid version format" in e for e in errors)


def test_validate_frontmatter_invalid_type() -> None:
    """Test validation catches invalid artifact type."""
    fm = ArtifactFrontmatter(
        kit_id="test-kit",
        kit_version="1.0.0",
        artifact_type="unknown",  # Invalid type
        artifact_path="agents/test.md",
    )

    errors = validate_frontmatter(fm)
    assert any("Invalid artifact_type" in e for e in errors)


def test_validate_artifact_valid(tmp_path: Path) -> None:
    """Test validating a valid artifact."""
    artifact = tmp_path / "test.md"
    artifact.write_text(
        "---\n"
        "name: test-agent\n"
        "description: A test agent\n"
        "__dot_agent:\n"
        "  kit_id: test-kit\n"
        "  kit_version: 1.0.0\n"
        "  artifact_type: agent\n"
        "  artifact_path: agents/test.md\n"
        "---\n\n"
        "# Test Agent",
        encoding="utf-8",
    )

    result = validate_artifact(artifact)
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_validate_artifact_missing_frontmatter(tmp_path: Path) -> None:
    """Test artifact without frontmatter."""
    artifact = tmp_path / "test.md"
    artifact.write_text("# Test Agent", encoding="utf-8")

    result = validate_artifact(artifact)
    assert result.is_valid is False
    assert any("No frontmatter" in e for e in result.errors)


def test_validate_artifact_nonexistent(tmp_path: Path) -> None:
    """Test validating non-existent artifact."""
    artifact = tmp_path / "nonexistent.md"

    result = validate_artifact(artifact)
    assert result.is_valid is False
    assert any("does not exist" in e for e in result.errors)


def test_validate_project(tmp_path: Path) -> None:
    """Test validating only managed artifacts in project."""
    from dot_agent_kit.io import save_project_config
    from dot_agent_kit.models import ConflictPolicy, InstalledKit, ProjectConfig

    # Create .claude structure with artifacts
    agents_dir = tmp_path / ".claude/agents"
    agents_dir.mkdir(parents=True)

    # Managed artifact (valid)
    managed_valid = agents_dir / "managed-valid.md"
    managed_valid.write_text(
        "---\n"
        "name: managed-valid\n"
        "description: A managed agent\n"
        "__dot_agent:\n"
        "  kit_id: test-kit\n"
        "  kit_version: 1.0.0\n"
        "  artifact_type: agent\n"
        "  artifact_path: agents/managed-valid.md\n"
        "---\n\n"
        "# Managed Valid",
        encoding="utf-8",
    )

    # Managed artifact (invalid - missing frontmatter)
    managed_invalid = agents_dir / "managed-invalid.md"
    managed_invalid.write_text("# No frontmatter", encoding="utf-8")

    # Unmanaged artifact (should NOT be validated)
    unmanaged = agents_dir / "unmanaged.md"
    unmanaged.write_text("# Unmanaged artifact", encoding="utf-8")

    # Create config that marks only two artifacts as managed
    config = ProjectConfig(
        version="1.0.0",
        default_conflict_policy=ConflictPolicy.ERROR,
        kits={
            "test-kit": InstalledKit(
                kit_id="test-kit",
                version="1.0.0",
                source="local",
                installed_at="2024-01-01T00:00:00Z",
                artifacts=[
                    "agents/managed-valid.md",
                    "agents/managed-invalid.md",
                ],
            )
        },
    )
    save_project_config(tmp_path, config)

    results = validate_project(tmp_path)
    # Should only validate 2 managed artifacts, not the unmanaged one
    assert len(results) == 2
    assert sum(r.is_valid for r in results) == 1


def test_validate_project_no_claude_dir(tmp_path: Path) -> None:
    """Test validating project with no .claude directory."""
    results = validate_project(tmp_path)
    assert len(results) == 0
