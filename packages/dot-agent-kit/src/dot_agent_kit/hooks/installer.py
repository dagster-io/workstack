"""Hook installation and removal operations."""

import shutil
from pathlib import Path

from dot_agent_kit.hooks.models import HookDefinition, HookEntry, HookMetadata
from dot_agent_kit.hooks.settings import (
    add_hook_to_settings,
    load_settings,
    remove_hooks_by_kit,
    save_settings,
)


def install_hooks(
    kit_id: str,
    hooks: list[HookDefinition],
    kit_path: Path,
    project_root: Path,
) -> int:
    """Install hooks from a kit.

    Args:
        kit_id: Kit identifier
        hooks: List of hook definitions from kit manifest
        kit_path: Path to kit directory containing hook scripts
        project_root: Project root directory

    Returns:
        Count of installed hooks

    Note:
        Copies hook scripts to .claude/hooks/{kit_id}/ with flattened structure.
        Updates settings.json with hook entries and metadata.
        Creates necessary directories automatically.
    """
    if not hooks:
        return 0

    # Prepare hook installation directory
    hooks_dir = project_root / ".claude" / "hooks" / kit_id
    if hooks_dir.exists():
        # Clean up existing installation
        shutil.rmtree(hooks_dir)
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Load current settings and remove any existing hooks from this kit
    settings_path = project_root / ".claude" / "settings.json"
    settings = load_settings(settings_path)
    settings, _ = remove_hooks_by_kit(settings, kit_id)

    installed_count = 0

    for hook_def in hooks:
        # Source script path in kit
        script_source = kit_path / hook_def.script

        if not script_source.exists():
            # Skip hooks with missing scripts
            continue

        # Flatten the path: just use the script filename
        script_filename = script_source.name
        script_dest = hooks_dir / script_filename

        # Copy script to hooks directory
        shutil.copy2(script_source, script_dest)

        # Build command using $CLAUDE_PROJECT_DIR for portability
        # Path relative to project root
        relative_hook_path = f".claude/hooks/{kit_id}/{script_filename}"
        command = f'python3 "$CLAUDE_PROJECT_DIR/{relative_hook_path}"'

        # Create hook entry
        metadata = HookMetadata(kit_id=kit_id, hook_id=hook_def.id)
        entry = HookEntry(
            command=command,
            timeout=hook_def.timeout,
            _dot_agent=metadata,
        )

        # Use wildcard matcher if none specified
        matcher = hook_def.matcher if hook_def.matcher is not None else "*"

        # Add to settings
        settings = add_hook_to_settings(
            settings,
            lifecycle=hook_def.lifecycle,
            matcher=matcher,
            entry=entry,
        )

        installed_count += 1

    # Save updated settings
    if installed_count > 0:
        save_settings(settings_path, settings)

    return installed_count


def remove_hooks(kit_id: str, project_root: Path) -> int:
    """Remove all hooks installed by a kit.

    Args:
        kit_id: Kit identifier
        project_root: Project root directory

    Returns:
        Count of removed hooks

    Note:
        Removes hook entries from settings.json.
        Deletes .claude/hooks/{kit_id}/ directory.
        Handles missing files gracefully.
    """
    # Load current settings
    settings_path = project_root / ".claude" / "settings.json"
    settings = load_settings(settings_path)

    # Remove hooks from settings
    updated_settings, removed_count = remove_hooks_by_kit(settings, kit_id)

    # Save if hooks were removed
    if removed_count > 0:
        save_settings(settings_path, updated_settings)

    # Delete hook scripts directory
    hooks_dir = project_root / ".claude" / "hooks" / kit_id
    if hooks_dir.exists():
        shutil.rmtree(hooks_dir)

    return removed_count
