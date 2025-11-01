"""Hook manifest I/O operations."""

from pathlib import Path

import tomli
import tomli_w

from dot_agent_kit.models import HookConfig, HookManifest


def load_hook_manifest(hooks_toml_path: Path) -> HookManifest:
    """Load hooks.toml manifest file.

    Args:
        hooks_toml_path: Path to hooks.toml file

    Returns:
        HookManifest with parsed hook configurations

    Raises:
        FileNotFoundError: If hooks.toml doesn't exist
        ValueError: If TOML is malformed or required fields are missing
    """
    if not hooks_toml_path.exists():
        raise FileNotFoundError(f"Hook manifest not found: {hooks_toml_path}")

    try:
        with open(hooks_toml_path, "rb") as f:
            data = tomli.load(f)
    except tomli.TOMLDecodeError as e:
        raise ValueError(f"Malformed TOML in {hooks_toml_path}: {e}") from e

    # Extract required fields
    kit_id = data.get("kit_id")
    if not kit_id:
        raise ValueError(f"Missing required field 'kit_id' in {hooks_toml_path}")

    kit_version = data.get("kit_version")
    if not kit_version:
        raise ValueError(f"Missing required field 'kit_version' in {hooks_toml_path}")

    # Parse hooks
    hooks = []
    for hook_data in data.get("hooks", []):
        hook = HookConfig(
            name=hook_data.get("name", ""),
            lifecycle=hook_data.get("lifecycle", ""),
            matcher=hook_data.get("matcher", ""),
            script=hook_data.get("script", ""),
            enabled=hook_data.get("enabled", True),
            description=hook_data.get("description"),
        )
        hooks.append(hook)

    manifest = HookManifest(
        kit_id=kit_id,
        kit_version=kit_version,
        hooks=hooks,
    )

    # Validate the manifest
    errors = manifest.validate()
    if errors:
        error_msg = "\n".join(f"  - {e}" for e in errors)
        raise ValueError(f"Invalid hook manifest in {hooks_toml_path}:\n{error_msg}")

    return manifest


def save_hook_manifest(hooks_toml_path: Path, manifest: HookManifest) -> None:
    """Save hooks.toml manifest file.

    This is used for enable/disable operations that modify the enabled flag.

    Args:
        hooks_toml_path: Path to hooks.toml file
        manifest: HookManifest to save
    """
    # Validate before saving
    errors = manifest.validate()
    if errors:
        error_msg = "\n".join(f"  - {e}" for e in errors)
        raise ValueError(f"Cannot save invalid hook manifest:\n{error_msg}")

    # Convert to dict
    data = {
        "kit_id": manifest.kit_id,
        "kit_version": manifest.kit_version,
        "hooks": [],
    }

    for hook in manifest.hooks:
        hook_data = {
            "name": hook.name,
            "lifecycle": hook.lifecycle,
            "matcher": hook.matcher,
            "script": hook.script,
            "enabled": hook.enabled,
        }
        if hook.description:
            hook_data["description"] = hook.description

        data["hooks"].append(hook_data)

    # Ensure parent directory exists
    hooks_toml_path.parent.mkdir(parents=True, exist_ok=True)

    with open(hooks_toml_path, "wb") as f:
        tomli_w.dump(data, f)


def update_hook_enabled(hooks_toml_path: Path, hook_name: str, enabled: bool) -> None:
    """Update the enabled flag for a specific hook.

    Args:
        hooks_toml_path: Path to hooks.toml file
        hook_name: Name of the hook to update
        enabled: New enabled state

    Raises:
        FileNotFoundError: If hooks.toml doesn't exist
        ValueError: If hook not found
    """
    manifest = load_hook_manifest(hooks_toml_path)

    # Find and update the hook
    updated_hooks = []
    found = False

    for hook in manifest.hooks:
        if hook.name == hook_name:
            # Create new hook with updated enabled flag
            updated_hook = HookConfig(
                name=hook.name,
                lifecycle=hook.lifecycle,
                matcher=hook.matcher,
                script=hook.script,
                enabled=enabled,
                description=hook.description,
            )
            updated_hooks.append(updated_hook)
            found = True
        else:
            updated_hooks.append(hook)

    if not found:
        raise ValueError(
            f"Hook '{hook_name}' not found in {hooks_toml_path}. "
            f"Available hooks: {', '.join(h.name for h in manifest.hooks)}"
        )

    # Save updated manifest
    updated_manifest = HookManifest(
        kit_id=manifest.kit_id,
        kit_version=manifest.kit_version,
        hooks=updated_hooks,
    )

    save_hook_manifest(hooks_toml_path, updated_manifest)
