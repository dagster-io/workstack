"""Tests for artifact validation."""

from pathlib import Path

from dot_agent_kit.io import save_project_config, validate_frontmatter
from dot_agent_kit.models import (
    ArtifactFrontmatter,
    ConflictPolicy,
    InstalledKit,
    ProjectConfig,
)
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
        "<!-- dot-agent-kit:\n"
        "kit_id: test-kit\n"
        "kit_version: 1.0.0\n"
        "artifact_type: agent\n"
        "artifact_path: agents/test.md\n"
        "-->\n\n"
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
    """Test validating all artifacts in project."""
    tmp_project = tmp_path

    # Create .claude structure with artifacts
    agents_dir = tmp_project / ".claude/agents"
    agents_dir.mkdir(parents=True)

    # Valid artifact
    valid = agents_dir / "valid.md"
    valid.write_text(
        "<!-- dot-agent-kit:\n"
        "kit_id: test-kit\n"
        "kit_version: 1.0.0\n"
        "artifact_type: agent\n"
        "artifact_path: agents/valid.md\n"
        "-->\n\n"
        "# Valid",
        encoding="utf-8",
    )

    # Invalid artifact
    invalid = agents_dir / "invalid.md"
    invalid.write_text("# No frontmatter", encoding="utf-8")

    # Create config file with kit that includes these artifacts
    config = ProjectConfig(
        version="1",
        default_conflict_policy=ConflictPolicy.ERROR,
        kits={
            "test-kit": InstalledKit(
                kit_id="test-kit",
                version="1.0.0",
                source="test",
                installed_at="2024-01-01T00:00:00Z",
                artifacts=[
                    ".claude/agents/valid.md",
                    ".claude/agents/invalid.md",
                ],
                conflict_policy="error",
            )
        },
    )
    save_project_config(tmp_project, config)

    results = validate_project(tmp_project)
    assert len(results) == 2
    assert sum(r.is_valid for r in results) == 1


def test_validate_project_no_claude_dir(tmp_path: Path) -> None:
    """Test validating project with no .claude directory."""
    tmp_project = tmp_path
    results = validate_project(tmp_project)
    assert len(results) == 0
