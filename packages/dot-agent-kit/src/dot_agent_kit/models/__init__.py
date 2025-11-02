"""Data models for dot-agent-kit."""

from dot_agent_kit.models.artifact import (
    ArtifactFrontmatter,
    ArtifactSource,
    validate_artifact_source,
)
from dot_agent_kit.models.config import (
    ConflictPolicy,
    InstalledKit,
    ProjectConfig,
    validate_conflict_policy,
)
from dot_agent_kit.models.installation import (
    InstallationContext,
    InstallationTarget,
    validate_installation_target,
)
from dot_agent_kit.models.kit import KitManifest
from dot_agent_kit.models.registry import RegistryEntry

__all__ = [
    "ArtifactFrontmatter",
    "ArtifactSource",
    "ConflictPolicy",
    "InstalledKit",
    "InstallationContext",
    "InstallationTarget",
    "ProjectConfig",
    "KitManifest",
    "RegistryEntry",
    "validate_artifact_source",
    "validate_conflict_policy",
    "validate_installation_target",
]
