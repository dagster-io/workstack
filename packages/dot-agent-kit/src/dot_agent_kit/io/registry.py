"""Registry I/O."""

from pathlib import Path

import yaml

from dot_agent_kit.models import RegistryEntry


def load_registry() -> list[RegistryEntry]:
    """Load registry.yaml from package data."""
    # Use importlib.resources to load from package data
    registry_path = Path(__file__).parent.parent / "data" / "registry.yaml"

    with open(registry_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "kits" not in data:
        return []

    return [
        RegistryEntry(
            kit_id=kit["kit_id"],
            source_type=kit["source_type"],
            description=kit["description"],
            version=kit["version"],
        )
        for kit in data["kits"]
    ]
