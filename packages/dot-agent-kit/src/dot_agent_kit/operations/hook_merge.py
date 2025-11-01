"""Operations for merging hooks by lifecycle and matcher."""

from dot_agent_kit.models.hook import HookEntry
from dot_agent_kit.models.settings import ClaudeSettings, MatcherGroup


def merge_hooks_into_groups(settings: ClaudeSettings) -> ClaudeSettings:
    """Group hooks by lifecycle+matcher.

    This function consolidates hooks that share the same lifecycle event
    and matcher pattern into single groups. It also validates that all
    hooks have proper structure before merging.

    Args:
        settings: The settings to process

    Returns:
        New ClaudeSettings with merged hooks

    Raises:
        ValueError: If any hook entry is invalid
    """
    merged_hooks: dict[str, list[MatcherGroup]] = {}

    for lifecycle, groups in settings.hooks.items():
        grouped_by_matcher: dict[str, list[dict[str, object]]] = {}

        for group in groups:
            matcher = group.matcher
            if matcher not in grouped_by_matcher:
                grouped_by_matcher[matcher] = []

            for hook in group.hooks:
                if not isinstance(hook, dict):
                    msg = f"Hook in {lifecycle}/{matcher} is not a dict"
                    raise ValueError(msg)

                # Validate hook structure using Pydantic
                HookEntry.model_validate(hook)

            grouped_by_matcher[matcher].extend(group.hooks)

        new_groups = []
        for matcher, hooks in grouped_by_matcher.items():
            new_groups.append(MatcherGroup(matcher=matcher, hooks=hooks))

        merged_hooks[lifecycle] = new_groups

    # Create new settings with merged hooks and preserved extra fields
    result_dict = {**settings.other, "hooks": merged_hooks}
    return ClaudeSettings.model_validate(result_dict)


def find_or_create_matcher_group(
    groups: list[MatcherGroup],
    matcher: str,
) -> MatcherGroup:
    """Find an existing matcher group or create a new one.

    Args:
        groups: List of existing matcher groups
        matcher: Matcher pattern to find

    Returns:
        Existing or new MatcherGroup
    """
    for group in groups:
        if group.matcher == matcher:
            return group

    return MatcherGroup(matcher=matcher, hooks=[])


def add_hook_to_settings(
    settings: ClaudeSettings,
    lifecycle: str,
    matcher: str,
    hook_entry: dict[str, object],
) -> ClaudeSettings:
    """Add a hook entry to settings at the appropriate location.

    This is a helper function that adds a hook to the correct lifecycle
    and matcher group, creating groups as needed.

    Args:
        settings: Current settings
        lifecycle: Lifecycle event (e.g., "PreToolUse")
        matcher: Tool matcher pattern (e.g., "Bash")
        hook_entry: Hook entry dict to add

    Returns:
        New ClaudeSettings with the hook added
    """
    new_hooks = dict(settings.hooks)

    if lifecycle not in new_hooks:
        new_hooks[lifecycle] = []

    groups = list(new_hooks[lifecycle])

    group = find_or_create_matcher_group(groups, matcher)

    new_hook_list = list(group.hooks)
    new_hook_list.append(hook_entry)

    new_group = MatcherGroup(matcher=matcher, hooks=new_hook_list)

    if group in groups:
        group_index = groups.index(group)
        groups[group_index] = new_group
    else:
        groups.append(new_group)

    new_hooks[lifecycle] = groups

    # Create new settings with updated hooks and preserved extra fields
    result_dict = {**settings.other, "hooks": new_hooks}
    return ClaudeSettings.model_validate(result_dict)


def cleanup_empty_groups(settings: ClaudeSettings) -> ClaudeSettings:
    """Remove matcher groups that have no hooks.

    Args:
        settings: Settings to clean up

    Returns:
        New ClaudeSettings with empty groups removed
    """
    cleaned_hooks: dict[str, list[MatcherGroup]] = {}

    for lifecycle, groups in settings.hooks.items():
        non_empty_groups = [g for g in groups if g.hooks]
        if non_empty_groups:
            cleaned_hooks[lifecycle] = non_empty_groups

    # Create new settings with cleaned hooks and preserved extra fields
    result_dict = {**settings.other, "hooks": cleaned_hooks}
    return ClaudeSettings.model_validate(result_dict)
