"""Artifact metadata models."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ArtifactSource(Enum):
    """Source type of an installed artifact."""

    MANAGED = "managed"  # Tracked in dot-agent.toml
    LOCAL = "local"  # Created manually, no kit association


@dataclass(frozen=True)
class InstalledArtifact:
    """Represents an installed artifact with its metadata."""

    artifact_type: str  # skill, command, agent
    artifact_name: str  # Display name
    file_path: Path  # Actual file location relative to .claude/
    source: ArtifactSource
    kit_id: str | None = None
    kit_version: str | None = None
