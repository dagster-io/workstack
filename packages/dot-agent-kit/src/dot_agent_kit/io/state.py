"""State file I/O for dot-agent.toml."""

from pathlib import Path

import click
import tomli
import tomli_w

from dot_agent_kit.models import ConflictPolicy, InstalledKit, ProjectConfig
from dot_agent_kit.models.hook import HookDefinition


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
            hooks_data = kit_data.get("hooks", [])
            hooks = _parse_hooks_from_state(hooks_data)

            kits[kit_id] = InstalledKit(
                kit_id=kit_data["kit_id"],
                version=kit_data["version"],
                source=kit_data["source"],
                installed_at=kit_data["installed_at"],
                artifacts=kit_data["artifacts"],
                conflict_policy=kit_data.get("conflict_policy", "error"),
                hooks=hooks,
            )

    # Parse conflict policy
    policy_str = data.get("default_conflict_policy", "error")
    policy = ConflictPolicy(policy_str)

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
        "default_conflict_policy": config.default_conflict_policy.value,
        "kits": {},
    }

    for kit_id, kit in config.kits.items():
        kit_dict = {
            "kit_id": kit.kit_id,
            "version": kit.version,
            "source": kit.source,
            "installed_at": kit.installed_at,
            "artifacts": kit.artifacts,
            "conflict_policy": kit.conflict_policy,
        }

        if kit.hooks:
            kit_dict["hooks"] = _serialize_hooks_for_state(kit.hooks)

        data["kits"][kit_id] = kit_dict

    with open(config_path, "wb") as f:
        tomli_w.dump(data, f)


def create_default_config() -> ProjectConfig:
    """Create default project configuration."""
    return ProjectConfig(
        version="1",
        default_conflict_policy=ConflictPolicy.ERROR,
        kits={},
    )


def _parse_hooks_from_state(hooks_data: list[dict[str, object]]) -> list[HookDefinition]:
    """Parse hooks from dot-agent.toml state.

    Args:
        hooks_data: List of hook dicts from TOML

    Returns:
        List of HookDefinition objects
    """
    hooks = []

    for i, hook_dict in enumerate(hooks_data):
        # Use lenient parsing for state files that may be corrupted
        try:
            hook = HookDefinition.model_validate(hook_dict)
            hooks.append(hook)
        except Exception as e:
            # Warn about invalid hooks in corrupted state files
            click.echo(f"Warning: Skipping invalid hook at index {i}: {e}", err=True)
            continue

    return hooks


def _serialize_hooks_for_state(hooks: list[HookDefinition]) -> list[dict[str, object]]:
    """Serialize hooks for dot-agent.toml.

    Args:
        hooks: List of HookDefinition objects

    Returns:
        List of dicts suitable for TOML serialization
    """
    return [hook.model_dump() for hook in hooks]
