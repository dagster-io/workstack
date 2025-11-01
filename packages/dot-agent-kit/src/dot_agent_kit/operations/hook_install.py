"""Operations for installing hooks to settings.json."""

import shutil
from pathlib import Path

from dot_agent_kit.io.settings_json import (
    get_hooks_dir,
    get_settings_path,
    modify_settings,
)
from dot_agent_kit.models.hook import HookDefinition, HookEntry, HookMetadata
from dot_agent_kit.operations.hook_merge import add_hook_to_settings, merge_hooks_into_groups


def install_hooks(
    kit_id: str,
    hook_definitions: list[HookDefinition],
    source_dir: Path,
) -> list[str]:
    """Install hooks from a kit.

    This function:
    1. Copies hook scripts to the hooks directory
    2. Adds hooks to settings.json with file locking
    3. Merges and saves atomically

    Args:
        kit_id: ID of the kit installing hooks
        hook_definitions: List of hook definitions from kit manifest
        source_dir: Source directory containing hook scripts

    Returns:
        List of installed hook IDs

    Raises:
        Exception: If installation fails
    """
    hooks_dir = get_hooks_dir(kit_id)
    hooks_dir.mkdir(parents=True, exist_ok=True)

    for hook_def in hook_definitions:
        source = source_dir / hook_def.script
        dest = hooks_dir / Path(hook_def.script).name
        shutil.copy2(source, dest)

    settings_path = get_settings_path()
    installed_ids: list[str] = []

    with modify_settings(settings_path) as (settings, save):
        for hook_def in hook_definitions:
            script_path = hooks_dir / Path(hook_def.script).name
            command = build_hook_command(script_path)

            # Create hook entry using Pydantic models for validation
            metadata = HookMetadata(kit_id=kit_id, hook_id=hook_def.hook_id)
            hook_entry_model = HookEntry(
                type="command",
                command=command,
                timeout=hook_def.timeout,
                **{"_dot_agent": metadata},  # Use alias via unpacking
            )

            settings = add_hook_to_settings(
                settings,
                hook_def.lifecycle,
                hook_def.matcher,
                hook_entry_model.model_dump(),
            )

            installed_ids.append(hook_def.hook_id)

        settings = merge_hooks_into_groups(settings)
        save(settings)

    return installed_ids


def build_hook_command(script_path: Path) -> str:
    """Build the command string for a hook script.

    Args:
        script_path: Path to the hook script

    Returns:
        Command string that executes the script
    """
    absolute_path = script_path.resolve()
    return f'python3 "{absolute_path}"'


def copy_hook_scripts(
    hook_definitions: list[HookDefinition],
    source_dir: Path,
    dest_dir: Path,
) -> None:
    """Copy hook scripts from source to destination.

    Args:
        hook_definitions: List of hook definitions
        source_dir: Source directory containing scripts
        dest_dir: Destination directory for scripts
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    for hook_def in hook_definitions:
        source = source_dir / hook_def.script
        dest = dest_dir / Path(hook_def.script).name

        if not source.exists():
            msg = f"Hook script not found: {source}"
            raise FileNotFoundError(msg)

        shutil.copy2(source, dest)
