"""Kit manifest I/O."""

from pathlib import Path

import tomli
import yaml

from dot_agent_kit.models import KitManifest
from dot_agent_kit.models.hook import HookDefinition


def load_kit_manifest(manifest_path: Path) -> KitManifest:
    """Load kit manifest file (supports both kit.yaml and kit.toml)."""
    if manifest_path.suffix == ".toml":
        return _load_toml_manifest(manifest_path)
    return _load_yaml_manifest(manifest_path)


def _load_yaml_manifest(manifest_path: Path) -> KitManifest:
    """Load kit.yaml manifest file."""
    with open(manifest_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return KitManifest(
        name=data["name"],
        version=data["version"],
        description=data["description"],
        artifacts=data.get("artifacts", {}),
        license=data.get("license"),
        homepage=data.get("homepage"),
        hooks=[],
    )


def _load_toml_manifest(manifest_path: Path) -> KitManifest:
    """Load kit.toml manifest file with hooks support."""
    with open(manifest_path, "rb") as f:
        data = tomli.load(f)

    hooks = _parse_hooks(data.get("hooks", []))

    return KitManifest(
        name=data["name"],
        version=data["version"],
        description=data["description"],
        artifacts=data.get("artifacts", {}),
        license=data.get("license"),
        homepage=data.get("homepage"),
        hooks=hooks,
    )


def _parse_hooks(hooks_data: list[dict[str, object]]) -> list[HookDefinition]:
    """Parse hooks array from TOML manifest.

    Args:
        hooks_data: List of hook definitions from manifest

    Returns:
        List of HookDefinition objects

    Raises:
        ValueError: If any hook definition is invalid
    """
    hooks = []

    for i, hook_dict in enumerate(hooks_data):
        try:
            hook = HookDefinition.model_validate(hook_dict)
            hooks.append(hook)
        except Exception as e:
            msg = f"Hook at index {i}: {e}"
            raise ValueError(msg) from e

    return hooks
