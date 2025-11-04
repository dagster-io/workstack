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


class ArtifactLevel(Enum):
    """Level at which an artifact is installed."""

    USER = "user"
    PROJECT = "project"

    def get_path(self) -> Path:
        """Return the base path for this artifact level."""
        if self == ArtifactLevel.USER:
            return Path.home() / ".claude"
        return Path.cwd() / ".claude"


@dataclass(frozen=True)
class InstalledArtifact:
    """Represents an installed artifact with its metadata."""

    artifact_type: ArtifactType
    artifact_name: str  # Display name
    file_path: Path  # Actual file location relative to .claude/
    source: ArtifactSource
    kit_id: str | None = None
    kit_version: str | None = None
    # Enhanced introspection fields
    settings_source: str | None = None  # "settings.json", "settings.local.json", "orphaned"
    level: ArtifactLevel | None = None  # USER or PROJECT
    lifecycle: str | None = None  # For hooks: UserPromptSubmit, PreToolUse, etc.
    matcher: str | None = None  # For hooks: file pattern
    timeout: int | None = None  # For hooks: timeout in seconds
    installed_at: str | None = None  # Installation timestamp
    file_count: dict[str, int] | None = None  # For skills: {"md": 5, "py": 3}
