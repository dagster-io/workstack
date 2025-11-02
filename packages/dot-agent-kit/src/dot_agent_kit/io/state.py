"""State file I/O for dot-agent.toml."""

from pathlib import Path

import tomli
import tomli_w

from dot_agent_kit.models import (
    InstalledKit,
    ProjectConfig,
    validate_conflict_policy,
)


def load_project_config(project_dir: Path) -> ProjectConfig | None:
    """Load dot-agent.toml from project directory.

    Returns None if file doesn't exist.
    """
    config_path = project_dir / "dot-agent.toml"
    if not config_path.exists():
        return None

    with open(config_path, "rb") as f:
        data = tomli.load(f)

    # Parse kits
    kits: dict[str, InstalledKit] = {}
    if "kits" in data:
        for kit_id, kit_data in data["kits"].items():
            kits[kit_id] = InstalledKit(
                kit_id=kit_data["kit_id"],
                version=kit_data["version"],
                source=kit_data["source"],
                installed_at=kit_data["installed_at"],
                artifacts=kit_data["artifacts"],
                conflict_policy=kit_data.get("conflict_policy", "error"),
            )

    # Parse conflict policy
    policy_str = data.get("default_conflict_policy", "error")
    policy = validate_conflict_policy(policy_str)

    return ProjectConfig(
        version=data.get("version", "1"),
        default_conflict_policy=policy,
        kits=kits,
    )


def save_project_config(project_dir: Path, config: ProjectConfig) -> None:
    """Save dot-agent.toml to project directory."""
    config_path = project_dir / "dot-agent.toml"

    # Convert ProjectConfig to dict
    data = {
        "version": config.version,
        "default_conflict_policy": config.default_conflict_policy,
        "kits": {},
    }

    for kit_id, kit in config.kits.items():
        data["kits"][kit_id] = {
            "kit_id": kit.kit_id,
            "version": kit.version,
            "source": kit.source,
            "installed_at": kit.installed_at,
            "artifacts": kit.artifacts,
            "conflict_policy": kit.conflict_policy,
        }

    with open(config_path, "wb") as f:
        tomli_w.dump(data, f)


def create_default_config() -> ProjectConfig:
    """Create default project configuration."""
    return ProjectConfig(
        version="1",
        default_conflict_policy="error",
        kits={},
    )
