"""Show command for displaying hook details."""

import json
import re
from pathlib import Path

import click
from pydantic import ValidationError

from dot_agent_kit.hooks.settings import extract_kit_id_from_command, get_all_hooks, load_settings


@click.command(name="show")
@click.argument("hook_spec")
def show_hook(hook_spec: str) -> None:
    """Show details for a specific hook.

    HOOK_SPEC should be in format: kit-id:hook-id
    """
    # Validate format
    if ":" not in hook_spec:
        click.echo(
            f"Error: Invalid hook spec '{hook_spec}'. Expected format: kit-id:hook-id",
            err=True,
        )
        raise SystemExit(1)

    # Parse spec
    parts = hook_spec.split(":", 1)
    if len(parts) != 2:
        click.echo(
            f"Error: Invalid hook spec '{hook_spec}'. Expected format: kit-id:hook-id",
            err=True,
        )
        raise SystemExit(1)

    kit_id, hook_id = parts

    # Load settings
    settings_path = Path.cwd() / ".claude" / "settings.json"

    if not settings_path.exists():
        click.echo(f"Error: Hook '{hook_spec}' not found.", err=True)
        raise SystemExit(1)

    try:
        settings = load_settings(settings_path)
    except (json.JSONDecodeError, ValidationError) as e:
        click.echo(f"Error loading settings.json: {e}", err=True)
        raise SystemExit(1) from None

    # Find matching hook
    hooks = get_all_hooks(settings)
    found = None

    for lifecycle, matcher, entry in hooks:
        entry_kit_id = extract_kit_id_from_command(entry.command)
        if entry_kit_id:
            hook_id_match = re.search(r"DOT_AGENT_HOOK_ID=(\S+)", entry.command)
            entry_hook_id = hook_id_match.group(1) if hook_id_match else None
            if entry_kit_id == kit_id and entry_hook_id == hook_id:
                found = (lifecycle, matcher, entry)
                break

    if not found:
        click.echo(f"Error: Hook '{hook_spec}' not found.", err=True)
        raise SystemExit(1)

    # Display hook details
    lifecycle, matcher, entry = found
    click.echo(f"Hook: {kit_id}:{hook_id}", err=False)
    click.echo(f"Lifecycle: {lifecycle}", err=False)
    click.echo(f"Matcher: {matcher}", err=False)
    click.echo(f"Timeout: {entry.timeout}s", err=False)
    click.echo(f"Command: {entry.command}", err=False)
