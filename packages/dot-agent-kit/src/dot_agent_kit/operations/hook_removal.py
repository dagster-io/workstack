"""Operations for removing hooks from settings.json."""

import shutil
from typing import Any

from dot_agent_kit.io.settings_json import (
    get_hooks_dir,
    get_settings_path,
    modify_settings,
)
from dot_agent_kit.models.settings import ClaudeSettings, MatcherGroup
from dot_agent_kit.operations.hook_merge import cleanup_empty_groups


def remove_hooks(kit_id: str) -> list[str]:
    """Remove all hooks for a kit.

    This function:
    1. Removes all hooks with matching kit_id from settings.json
    2. Cleans up empty matcher groups
    3. Saves atomically with file locking
    4. Deletes hook script files

    Args:
        kit_id: ID of the kit to remove hooks for

    Returns:
        List of removed hook IDs

    Raises:
        Exception: If removal fails
    """
    settings_path = get_settings_path()
    removed_ids: list[str] = []

    with modify_settings(settings_path) as (settings, save):
        for _lifecycle, groups in settings.hooks.items():
            for group in groups:
                for hook in group.hooks:
                    if not isinstance(hook, dict):
                        continue

                    metadata = hook.get("_dot_agent", {})
                    if isinstance(metadata, dict) and metadata.get("kit_id") == kit_id:
                        hook_id = metadata.get("hook_id")
                        if isinstance(hook_id, str):
                            removed_ids.append(hook_id)

        settings = remove_hooks_by_kit_id(settings, kit_id)
        settings = cleanup_empty_groups(settings)
        save(settings)

    hooks_dir = get_hooks_dir(kit_id)
    if hooks_dir.exists():
        shutil.rmtree(hooks_dir)

    return list(set(removed_ids))


def remove_hooks_by_kit_id(settings: ClaudeSettings, kit_id: str) -> ClaudeSettings:
    """Remove all hooks with matching kit_id from settings.

    Args:
        settings: Current settings
        kit_id: Kit ID to match

    Returns:
        New ClaudeSettings with matching hooks removed
    """
    filtered_hooks: dict[str, list[MatcherGroup]] = {}

    for lifecycle, groups in settings.hooks.items():
        filtered_groups = []

        for group in groups:
            filtered_hook_list = [
                hook for hook in group.hooks if not _is_hook_from_kit(hook, kit_id)
            ]

            if filtered_hook_list:
                filtered_groups.append(
                    MatcherGroup(matcher=group.matcher, hooks=filtered_hook_list)
                )

        if filtered_groups:
            filtered_hooks[lifecycle] = filtered_groups

    # Create new settings with filtered hooks and preserved extra fields
    result_dict = {**settings.other, "hooks": filtered_hooks}
    return ClaudeSettings.model_validate(result_dict)


def remove_hook_by_id(
    settings: ClaudeSettings,
    kit_id: str,
    hook_id: str,
) -> ClaudeSettings:
    """Remove a specific hook by kit_id and hook_id.

    Args:
        settings: Current settings
        kit_id: Kit ID to match
        hook_id: Hook ID to match

    Returns:
        New ClaudeSettings with the specific hook removed
    """
    filtered_hooks: dict[str, list[MatcherGroup]] = {}

    for lifecycle, groups in settings.hooks.items():
        filtered_groups = []

        for group in groups:
            filtered_hook_list = [
                hook for hook in group.hooks if not _is_specific_hook(hook, kit_id, hook_id)
            ]

            if filtered_hook_list:
                filtered_groups.append(
                    MatcherGroup(matcher=group.matcher, hooks=filtered_hook_list)
                )

        if filtered_groups:
            filtered_hooks[lifecycle] = filtered_groups

    # Create new settings with filtered hooks and preserved extra fields
    result_dict = {**settings.other, "hooks": filtered_hooks}
    return ClaudeSettings.model_validate(result_dict)


def _is_hook_from_kit(hook: dict[str, Any], kit_id: str) -> bool:
    """Check if a hook entry is from the specified kit.

    Args:
        hook: Hook entry dict
        kit_id: Kit ID to match

    Returns:
        True if hook is from the kit, False otherwise
    """
    if not isinstance(hook, dict):
        return False

    metadata = hook.get("_dot_agent", {})
    if not isinstance(metadata, dict):
        return False

    return metadata.get("kit_id") == kit_id


def _is_specific_hook(hook: dict[str, Any], kit_id: str, hook_id: str) -> bool:
    """Check if a hook entry matches both kit_id and hook_id.

    Args:
        hook: Hook entry dict
        kit_id: Kit ID to match
        hook_id: Hook ID to match

    Returns:
        True if hook matches both IDs, False otherwise
    """
    if not isinstance(hook, dict):
        return False

    metadata = hook.get("_dot_agent", {})
    if not isinstance(metadata, dict):
        return False

    return metadata.get("kit_id") == kit_id and metadata.get("hook_id") == hook_id
