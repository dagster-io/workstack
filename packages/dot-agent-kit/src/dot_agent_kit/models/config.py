"""Configuration models for dot-agent-kit."""

from dataclasses import dataclass, field, replace
from enum import Enum

from dot_agent_kit.models.hook import HookDefinition


class ConflictPolicy(Enum):
    """How to handle file conflicts during installation."""

    ERROR = "error"  # Fail on conflicts (default)
    SKIP = "skip"  # Skip conflicting files
    OVERWRITE = "overwrite"  # Replace existing files
    MERGE = "merge"  # Intelligent merging (future)


@dataclass(frozen=True)
class InstalledKit:
    """Represents an installed kit in dot-agent.toml."""

    kit_id: str
    version: str
    source: str
    installed_at: str
    artifacts: list[str]
    conflict_policy: str = "error"
    hooks: list[HookDefinition] = field(default_factory=list)


@dataclass(frozen=True)
class ProjectConfig:
    """Project configuration from dot-agent.toml."""

    version: str
    default_conflict_policy: ConflictPolicy
    kits: dict[str, InstalledKit]

    def update_kit(self, kit: InstalledKit) -> "ProjectConfig":
        """Return new config with updated kit (maintaining immutability)."""
        new_kits = {**self.kits, kit.kit_id: kit}
        return replace(self, kits=new_kits)
