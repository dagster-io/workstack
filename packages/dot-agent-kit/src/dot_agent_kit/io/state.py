"""State file I/O for dot-agent.toml."""

from pathlib import Path

import click
import tomli
import tomli_w

from dot_agent_kit.hooks.models import HookDefinition
from dot_agent_kit.models import InstalledKit, ProjectConfig


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
            # Parse hooks if present
            hooks: list[HookDefinition] = []
            if "hooks" in kit_data:
                hooks = [HookDefinition.model_validate(h) for h in kit_data["hooks"]]

            kits[kit_id] = InstalledKit(
                kit_id=kit_data["kit_id"],
                version=kit_data["version"],
                source=kit_data["source"],
                installed_at=kit_data["installed_at"],
                artifacts=kit_data["artifacts"],
                hooks=hooks,
            )

    return ProjectConfig(
        version=data.get("version", "1"),
        kits=kits,
    )


def require_project_config(project_dir: Path) -> ProjectConfig:
    """Load dot-agent.toml and exit with error if not found.

    This is a convenience wrapper around load_project_config that enforces
    the config must exist, displaying a helpful error message if not.

    Returns:
        ProjectConfig if found

    Raises:
        SystemExit: If dot-agent.toml not found
    """
    config = load_project_config(project_dir)
    if config is None:
        msg = "Error: No dot-agent.toml found. Run 'dot-agent kit init' to create one."
        click.echo(msg, err=True)
        raise SystemExit(1)
    return config


def save_project_config(project_dir: Path, config: ProjectConfig) -> None:
    """Save dot-agent.toml to project directory."""
    config_path = project_dir / "dot-agent.toml"

    # Convert ProjectConfig to dict
    data = {
        "version": config.version,
        "kits": {},
    }

    for kit_id, kit in config.kits.items():
        kit_data = {
            "kit_id": kit.kit_id,
            "version": kit.version,
            "source": kit.source,
            "installed_at": kit.installed_at,
            "artifacts": kit.artifacts,
        }

        # Add hooks if present
        if kit.hooks:
            kit_data["hooks"] = [h.model_dump(mode="json", exclude_none=True) for h in kit.hooks]

        data["kits"][kit_id] = kit_data

    with open(config_path, "wb") as f:
        tomli_w.dump(data, f)


def create_default_config() -> ProjectConfig:
    """Create default project configuration."""
    return ProjectConfig(
        version="1",
        kits={},
    )
