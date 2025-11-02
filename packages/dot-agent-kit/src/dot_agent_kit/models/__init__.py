"""Data models for dot-agent-kit."""

from dot_agent_kit.models.artifact import ArtifactFrontmatter
from dot_agent_kit.models.config import ConflictPolicy, InstalledKit, ProjectConfig
from dot_agent_kit.models.installation import InstallationContext
from dot_agent_kit.models.kit import KitManifest
from dot_agent_kit.models.registry import RegistryEntry

__all__ = [
    "ArtifactFrontmatter",
    "ConflictPolicy",
    "InstalledKit",
    "InstallationContext",
    "ProjectConfig",
    "KitManifest",
    "RegistryEntry",
]
