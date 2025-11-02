"""Configuration models for dot-agent-kit."""

from dataclasses import dataclass, replace
from typing import Literal, cast

ConflictPolicy = Literal["error", "skip", "overwrite", "merge"]


def validate_conflict_policy(value: str) -> ConflictPolicy:
    """Validate and return conflict policy.

    Args:
        value: String to validate

    Returns:
        Valid ConflictPolicy

    Raises:
        ValueError: If value is not a valid conflict policy
    """
    if value not in ("error", "skip", "overwrite", "merge"):
        raise ValueError(f"Invalid conflict policy: {value}")
    return cast(ConflictPolicy, value)


@dataclass(frozen=True)
class InstalledKit:
    """Represents an installed kit in dot-agent.toml."""

    kit_id: str
    version: str
    source: str
    installed_at: str
    artifacts: list[str]
    conflict_policy: str = "error"


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
