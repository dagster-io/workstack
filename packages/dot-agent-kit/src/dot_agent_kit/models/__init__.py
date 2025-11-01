"""Data models for dot-agent-kit."""

from dot_agent_kit.models.artifact import ArtifactFrontmatter
from dot_agent_kit.models.config import ConflictPolicy, InstalledKit, ProjectConfig
from dot_agent_kit.models.hook import HookConfig, HookManifest
from dot_agent_kit.models.installation import InstallationContext, InstallationTarget
from dot_agent_kit.models.kit import KitManifest
from dot_agent_kit.models.registry import RegistryEntry

__all__ = [
    "ArtifactFrontmatter",
    "ConflictPolicy",
    "HookConfig",
    "HookManifest",
    "InstalledKit",
    "InstallationContext",
    "InstallationTarget",
    "ProjectConfig",
    "KitManifest",
    "RegistryEntry",
]
