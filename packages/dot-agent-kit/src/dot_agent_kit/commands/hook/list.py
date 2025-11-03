"""List command for showing installed hooks."""

import json
import re
from pathlib import Path

import click
from pydantic import ValidationError

from dot_agent_kit.hooks.settings import extract_kit_id_from_command, get_all_hooks, load_settings


@click.command(name="list")
def list_hooks() -> None:
    """List all installed hooks."""
    # Load settings from project directory
    settings_path = Path.cwd() / ".claude" / "settings.json"

    if not settings_path.exists():
        click.echo("No hooks installed.", err=False)
        click.echo("Total: 0 hook(s)", err=False)
        raise SystemExit(0)

    try:
        settings = load_settings(settings_path)
    except (json.JSONDecodeError, ValidationError) as e:
        click.echo(f"Error loading settings.json: {e}", err=True)
        raise SystemExit(1) from None

    # Extract all hooks
    hooks = get_all_hooks(settings)

    if not hooks:
        click.echo("No hooks installed.", err=False)
        click.echo("Total: 0 hook(s)", err=False)
        raise SystemExit(0)

    # Display hooks
    for lifecycle, matcher, entry in hooks:
        kit_id = extract_kit_id_from_command(entry.command)
        if kit_id:
            # Extract hook_id from command as well
            hook_id_match = re.search(r"DOT_AGENT_HOOK_ID=(\S+)", entry.command)
            hook_id = hook_id_match.group(1) if hook_id_match else "unknown"
            hook_spec = f"{kit_id}:{hook_id}"
        else:
            # Local hook without kit metadata - show command
            hook_spec = f"local: {entry.command[:50]}"
        click.echo(f"{hook_spec} [{lifecycle} / {matcher}]", err=False)

    click.echo(f"Total: {len(hooks)} hook(s)", err=False)
