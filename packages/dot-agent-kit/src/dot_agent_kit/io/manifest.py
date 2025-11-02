"""Kit manifest I/O."""

from pathlib import Path

import yaml

from dot_agent_kit.hooks.models import HookDefinition
from dot_agent_kit.models import KitManifest


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
                script=hook_data["script"],
                description=hook_data["description"],
                timeout=hook_data.get("timeout", 30),
            )
            hooks.append(hook)

    return KitManifest(
        name=data["name"],
        version=data["version"],
        description=data["description"],
        artifacts=data.get("artifacts", {}),
        license=data.get("license"),
        homepage=data.get("homepage"),
        hooks=hooks,
    )
