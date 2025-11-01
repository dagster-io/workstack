"""Hook management commands."""

from collections.abc import Generator
from typing import NamedTuple

import click

from dot_agent_kit.io.settings_json import get_settings_path, load_settings
from dot_agent_kit.models.hook import HookEntry
from dot_agent_kit.models.settings import ClaudeSettings


class HookWithMetadata(NamedTuple):
    """A hook entry with its metadata and context."""

    lifecycle: str
    matcher: str
    hook: dict[str, object]
    metadata: dict[str, object]


@click.group()
def hook() -> None:
    """Manage Claude Code hooks."""


def _iter_hooks_with_metadata(
    settings: ClaudeSettings,
) -> Generator[HookWithMetadata]:
    """Iterate through all hooks with their metadata.

    Yields:
        HookWithMetadata instances containing lifecycle, matcher, hook dict, and metadata.
    """
    for lifecycle, groups in settings.hooks.items():
        for group in groups:
            for hook_dict in group.hooks:
                if not isinstance(hook_dict, dict):
                    continue

                metadata = hook_dict.get("_dot_agent")
                if not isinstance(metadata, dict):
                    continue

                yield HookWithMetadata(
                    lifecycle=lifecycle,
                    matcher=group.matcher,
                    hook=hook_dict,
                    metadata=metadata,
                )


@hook.command()
def list() -> None:
    """List all installed hooks in the current project."""
    settings_path = get_settings_path()
    if not settings_path.exists():
        click.echo("  No hooks configured", err=True)
        return

    settings = load_settings(settings_path)

    if not settings.hooks:
        click.echo("  No hooks configured", err=True)
        return

    total_hooks = 0
    for lifecycle, matcher, _hook_dict, metadata in _iter_hooks_with_metadata(settings):
        kit_id = metadata.get("kit_id", "unknown")
        hook_id = metadata.get("hook_id", "unknown")

        click.echo(f"  {kit_id}:{hook_id} [{lifecycle} / {matcher}]")
        total_hooks += 1

    if total_hooks == 0:
        click.echo("  No hooks configured", err=True)
    else:
        click.echo(f"\nTotal: {total_hooks} hook(s)")


@hook.command()
@click.argument("hook_spec")
def show(hook_spec: str) -> None:
    """Show detailed information about a hook.

    HOOK_SPEC should be in the format: kit-id:hook-id
    """
    if ":" not in hook_spec:
        click.echo("Error: Hook spec must be in format kit-id:hook-id", err=True)
        raise SystemExit(1)

    kit_id, hook_id = hook_spec.split(":", 1)

    settings_path = get_settings_path()
    if not settings_path.exists():
        click.echo("Error: No settings.json found", err=True)
        raise SystemExit(1)

    settings = load_settings(settings_path)

    for lifecycle, matcher, hook_dict, metadata in _iter_hooks_with_metadata(settings):
        if metadata.get("kit_id") == kit_id and metadata.get("hook_id") == hook_id:
            _display_hook_details(hook_dict, lifecycle, matcher)
            return

    click.echo(f"Error: Hook '{hook_spec}' not found", err=True)
    raise SystemExit(1)


def _display_hook_details(hook_dict: dict[str, object], lifecycle: str, matcher: str) -> None:
    """Display detailed hook information."""
    metadata = hook_dict.get("_dot_agent")
    if not isinstance(metadata, dict):
        return

    kit_id = metadata.get("kit_id", "unknown")
    hook_id = metadata.get("hook_id", "unknown")
    command = hook_dict.get("command", "")
    timeout = hook_dict.get("timeout", 30)

    click.echo(f"Hook: {kit_id}:{hook_id}")
    click.echo(f"Lifecycle: {lifecycle}")
    click.echo(f"Matcher: {matcher}")
    click.echo(f"Timeout: {timeout}s")
    click.echo(f"Command: {command}")


@hook.command()
def validate() -> None:
    """Validate settings.json integrity."""
    settings_path = get_settings_path()

    if not settings_path.exists():
        click.echo("✓ No settings.json found (nothing to validate)")
        return

    try:
        settings = load_settings(settings_path)

        issues = []

        for lifecycle, groups in settings.hooks.items():
            for group in groups:
                for i, hook_dict in enumerate(group.hooks):
                    if not isinstance(hook_dict, dict):
                        issues.append(
                            f"Invalid hook entry in {lifecycle}/{group.matcher} at index {i}"
                        )
                        continue

                    # Validate hook entry using Pydantic
                    HookEntry.model_validate(hook_dict)

        if issues:
            click.echo("✗ Validation failed:", err=True)
            for issue in issues:
                click.echo(f"  - {issue}", err=True)
            raise SystemExit(1)

        click.echo("✓ Settings validation passed")

    except Exception as e:
        click.echo(f"✗ Failed to load settings.json: {e}", err=True)
        raise SystemExit(1) from e
