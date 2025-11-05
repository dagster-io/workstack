"""Registry models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RegistryEntry:
    """Kit entry in the registry."""

    kit_id: str  # Globally unique kit identifier
    source_type: str  # "bundled" or "package"
    description: str
    version: str
