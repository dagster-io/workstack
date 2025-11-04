"""Artifact metadata models."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal


class ArtifactSource(Enum):
    """Source type of an installed artifact."""

    MANAGED = "managed"  # Tracked in dot-agent.toml
    LOCAL = "local"  # Created manually, no kit association


# Artifact type literals
ArtifactType = Literal["skill", "command", "agent", "hook"]
ArtifactTypePlural = Literal["skills", "commands", "agents", "hooks"]

# Mapping from singular to plural forms
ARTIFACT_TYPE_PLURALS: dict[ArtifactType, ArtifactTypePlural] = {
    "skill": "skills",
    "command": "commands",
    "agent": "agents",
    "hook": "hooks",
}


@dataclass(frozen=True)
class InstalledArtifact:
    """Represents an installed artifact with its metadata."""

    artifact_type: ArtifactType
    artifact_name: str  # Display name
    file_path: Path  # Actual file location relative to .claude/
    source: ArtifactSource
    kit_id: str | None = None
    kit_version: str | None = None
