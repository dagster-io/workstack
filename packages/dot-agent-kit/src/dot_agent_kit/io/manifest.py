"""Kit manifest I/O."""

from pathlib import Path

import yaml

from dot_agent_kit.hooks.models import HookDefinition
from dot_agent_kit.models.kit import KitCliCommandDefinition, KitManifest


def load_kit_manifest(manifest_path: Path) -> KitManifest:
    """Load kit.yaml manifest file."""
    with open(manifest_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Parse hooks if present
    hooks = []
    if "hooks" in data and data["hooks"]:
        for hook_data in data["hooks"]:
            hook = HookDefinition(
                id=hook_data["id"],
                lifecycle=hook_data["lifecycle"],
                matcher=hook_data.get("matcher"),
                invocation=hook_data["invocation"],
                description=hook_data["description"],
                timeout=hook_data.get("timeout", 30),
            )
            hooks.append(hook)

    # Parse kit cli commands if present
    kit_cli_commands = []
    if "kit_cli_commands" in data and data["kit_cli_commands"]:
        for command_data in data["kit_cli_commands"]:
            command = KitCliCommandDefinition(
                name=command_data["name"],
                path=command_data["path"],
                description=command_data["description"],
            )
            kit_cli_commands.append(command)

    return KitManifest(
        name=data["name"],
        version=data["version"],
        description=data["description"],
        artifacts=data.get("artifacts", {}),
        license=data.get("license"),
        homepage=data.get("homepage"),
        hooks=hooks,
        kit_cli_commands=kit_cli_commands,
    )
