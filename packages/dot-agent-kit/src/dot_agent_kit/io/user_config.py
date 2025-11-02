"""User-level configuration management for ~/.claude/dot-agent.toml."""

from pathlib import Path
from typing import Any

import tomli
import tomli_w

from dot_agent_kit.models import (
    InstalledKit,
    ProjectConfig,
    validate_conflict_policy,
)


def get_user_claude_dir() -> Path:
    """Get the user-level .claude directory (~/.claude)."""
    return Path.home() / ".claude"


def get_user_config_path() -> Path:
    """Get the user-level dot-agent.toml path."""
    return get_user_claude_dir() / "dot-agent.toml"


def load_user_config() -> ProjectConfig:
    """Load user-level dot-agent.toml from ~/.claude/.

    Returns default config if file doesn't exist.
    """
    config_path = get_user_config_path()
    if not config_path.exists():
        return create_default_user_config()

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


def save_user_config(config: ProjectConfig) -> None:
    """Save user-level dot-agent.toml to ~/.claude/."""
    config_path = get_user_config_path()

    # Ensure ~/.claude directory exists
    user_claude_dir = get_user_claude_dir()
    if not user_claude_dir.exists():
        user_claude_dir.mkdir(parents=True)

    # Convert ProjectConfig to dict
    data: dict[str, Any] = {
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


def create_default_user_config() -> ProjectConfig:
    """Create default user-level configuration."""
    return ProjectConfig(
        version="1",
        default_conflict_policy="error",
        kits={},
    )
