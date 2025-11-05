"""Tests for artifact formatting functions."""

from pathlib import Path

from dot_agent_kit.commands.artifact.formatting import (
    format_artifact_header,
    format_compact_artifact_line,
    format_compact_list,
    format_hook_metadata,
    format_level_indicator,
    format_source_indicator,
    format_verbose_list,
)
from dot_agent_kit.models.artifact import ArtifactLevel, ArtifactSource, InstalledArtifact


def test_format_level_indicator_user() -> None:
    """Test level indicator formatting for user level."""
    result = format_level_indicator(ArtifactLevel.USER)
    # Should contain [U] but may have ANSI codes
    assert "[U]" in result


def test_format_level_indicator_project() -> None:
    """Test level indicator formatting for project level."""
    result = format_level_indicator(ArtifactLevel.PROJECT)
    # Should contain [P] but may have ANSI codes
    assert "[P]" in result


def test_format_source_indicator_local() -> None:
    """Test source indicator for local artifacts."""
    artifact = InstalledArtifact(
        artifact_type="skill",
        artifact_name="test-skill",
        file_path=Path("skills/test-skill/SKILL.md"),
        source=ArtifactSource.LOCAL,
        level=ArtifactLevel.USER,
    )

    result = format_source_indicator(artifact)
    assert "[local]" in result


def test_format_source_indicator_managed() -> None:
    """Test source indicator for managed artifacts."""
    artifact = InstalledArtifact(
        artifact_type="skill",
        artifact_name="test-skill",
        file_path=Path("skills/test-skill/SKILL.md"),
        source=ArtifactSource.MANAGED,
        level=ArtifactLevel.USER,
        kit_id="my-kit",
        kit_version="1.0.0",
    )

    result = format_source_indicator(artifact)
    assert "my-kit@1.0.0" in result


def test_format_compact_artifact_line() -> None:
    """Test compact single-line artifact formatting."""
    artifact = InstalledArtifact(
        artifact_type="command",
        artifact_name="test-cmd",
        file_path=Path("commands/test-cmd.md"),
        source=ArtifactSource.LOCAL,
        level=ArtifactLevel.PROJECT,
    )

    result = format_compact_artifact_line(artifact)
    assert "test-cmd" in result
    assert "[P]" in result
    assert "[local]" in result


def test_format_artifact_header() -> None:
    """Test artifact header formatting without absolute path."""
    artifact = InstalledArtifact(
        artifact_type="skill",
        artifact_name="my-skill",
        file_path=Path("skills/my-skill/SKILL.md"),
        source=ArtifactSource.MANAGED,
        level=ArtifactLevel.USER,
        kit_id="test-kit",
        kit_version="2.0.0",
    )

    result = format_artifact_header(artifact)
    assert "my-skill" in result
    assert "skill" in result
    assert "user" in result
    assert "managed" in result
    assert "test-kit" in result
    assert "2.0.0" in result
    assert str(artifact.file_path) in result


def test_format_artifact_header_with_absolute_path() -> None:
    """Test artifact header formatting with absolute path."""
    artifact = InstalledArtifact(
        artifact_type="skill",
        artifact_name="my-skill",
        file_path=Path("skills/my-skill/SKILL.md"),
        source=ArtifactSource.MANAGED,
        level=ArtifactLevel.USER,
        kit_id="test-kit",
        kit_version="2.0.0",
    )

    absolute_path = Path("/home/user/.claude/skills/my-skill/SKILL.md")
    result = format_artifact_header(artifact, absolute_path)
    assert "my-skill" in result
    assert str(absolute_path) in result
    # Should display absolute path, not the relative path as a separate item
    # The relative path may appear as part of the absolute path, but should not
    # be listed as the main Path value when absolute_path is provided
    assert f"Path: {artifact.file_path}" not in result
    assert f"Path: {absolute_path}" in result


def test_format_hook_metadata_with_settings_json() -> None:
    """Test hook metadata formatting with settings.json source."""
    artifact = InstalledArtifact(
        artifact_type="hook",
        artifact_name="test-hook",
        file_path=Path("hooks/test-hook.py"),
        source=ArtifactSource.LOCAL,
        level=ArtifactLevel.PROJECT,
        settings_source="settings.json",
    )

    result = format_hook_metadata(artifact)
    assert "settings.json" in result
    # Should NOT have warning for settings.json
    assert "⚠️" not in result


def test_format_hook_metadata_with_settings_local() -> None:
    """Test hook metadata formatting with settings.local.json source."""
    artifact = InstalledArtifact(
        artifact_type="hook",
        artifact_name="test-hook",
        file_path=Path("hooks/test-hook.py"),
        source=ArtifactSource.LOCAL,
        level=ArtifactLevel.PROJECT,
        settings_source="settings.local.json",
    )

    result = format_hook_metadata(artifact)
    assert "settings.local.json" in result
    # Should have warning for settings.local.json
    assert "⚠️" in result


def test_format_hook_metadata_non_hook() -> None:
    """Test hook metadata returns empty string for non-hook artifacts."""
    artifact = InstalledArtifact(
        artifact_type="command",
        artifact_name="test-cmd",
        file_path=Path("commands/test-cmd.md"),
        source=ArtifactSource.LOCAL,
        level=ArtifactLevel.PROJECT,
    )

    result = format_hook_metadata(artifact)
    assert result == ""


def test_format_compact_list_empty() -> None:
    """Test compact list formatting with empty list."""
    result = format_compact_list([])
    assert result == ""


def test_format_compact_list_grouped_by_type() -> None:
    """Test compact list groups artifacts by type."""
    artifacts = [
        InstalledArtifact(
            artifact_type="skill",
            artifact_name="skill-a",
            file_path=Path("skills/skill-a/SKILL.md"),
            source=ArtifactSource.LOCAL,
            level=ArtifactLevel.USER,
        ),
        InstalledArtifact(
            artifact_type="command",
            artifact_name="cmd-a",
            file_path=Path("commands/cmd-a.md"),
            source=ArtifactSource.LOCAL,
            level=ArtifactLevel.PROJECT,
        ),
        InstalledArtifact(
            artifact_type="skill",
            artifact_name="skill-b",
            file_path=Path("skills/skill-b/SKILL.md"),
            source=ArtifactSource.LOCAL,
            level=ArtifactLevel.USER,
        ),
    ]

    result = format_compact_list(artifacts)

    # Should have type headers
    assert "Skills:" in result or "skills:" in result.lower()
    assert "Commands:" in result or "commands:" in result.lower()

    # Should have artifact names
    assert "skill-a" in result
    assert "skill-b" in result
    assert "cmd-a" in result


def test_format_verbose_list_empty() -> None:
    """Test verbose list formatting with empty list."""
    result = format_verbose_list([])
    assert result == ""


def test_format_verbose_list_with_metadata() -> None:
    """Test verbose list includes full metadata."""
    artifacts = [
        InstalledArtifact(
            artifact_type="skill",
            artifact_name="test-skill",
            file_path=Path("skills/test-skill/SKILL.md"),
            source=ArtifactSource.MANAGED,
            level=ArtifactLevel.USER,
            kit_id="my-kit",
            kit_version="1.0.0",
        ),
        InstalledArtifact(
            artifact_type="command",
            artifact_name="test-cmd",
            file_path=Path("commands/test-cmd.md"),
            source=ArtifactSource.LOCAL,
            level=ArtifactLevel.PROJECT,
        ),
    ]

    result = format_verbose_list(artifacts)

    # Should contain artifact names
    assert "test-skill" in result
    assert "test-cmd" in result

    # Should contain metadata
    assert "skill" in result
    assert "command" in result
    assert "user" in result
    assert "project" in result
    assert "managed" in result
    assert "local" in result
    assert "my-kit" in result
    assert "1.0.0" in result


def test_format_verbose_list_with_hooks() -> None:
    """Test verbose list includes hook-specific metadata."""
    artifacts = [
        InstalledArtifact(
            artifact_type="hook",
            artifact_name="test-hook",
            file_path=Path("hooks/test-hook.py"),
            source=ArtifactSource.LOCAL,
            level=ArtifactLevel.PROJECT,
            settings_source="settings.local.json",
        ),
    ]

    result = format_verbose_list(artifacts)

    # Should contain hook metadata
    assert "test-hook" in result
    assert "settings.local.json" in result
    assert "⚠️" in result  # Warning for local settings
