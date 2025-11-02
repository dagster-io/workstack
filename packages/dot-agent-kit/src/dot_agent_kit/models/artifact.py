"""Artifact metadata models."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast


@dataclass(frozen=True)
class ArtifactFrontmatter:
    """Frontmatter metadata embedded in artifact files."""

    kit_id: str
    kit_version: str
    artifact_type: str
    artifact_path: str


ArtifactSource = Literal["managed", "unmanaged", "local"]


def validate_artifact_source(value: str) -> ArtifactSource:
    """Validate and return artifact source.

    Args:
        value: String to validate

    Returns:
        Valid ArtifactSource

    Raises:
        ValueError: If value is not a valid artifact source
    """
    if value not in ("managed", "unmanaged", "local"):
        raise ValueError(f"Invalid artifact source: {value}")
    return cast(ArtifactSource, value)


@dataclass(frozen=True)
class InstalledArtifact:
    """Represents an installed artifact with its metadata."""

    artifact_type: str  # skill, command, agent
    artifact_name: str  # Display name
    file_path: Path  # Actual file location relative to .claude/
    source: ArtifactSource
    kit_id: str | None = None
    kit_version: str | None = None
