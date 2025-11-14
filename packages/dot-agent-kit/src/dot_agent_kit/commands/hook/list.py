"""List command for showing installed hooks."""

import json
import re
from pathlib import Path

import click
from pydantic import ValidationError

from dot_agent_kit.cli.output import user_output
from dot_agent_kit.hooks.settings import extract_kit_id_from_command, get_all_hooks, load_settings


def _list_hooks_impl() -> None:
    """Implementation of list command logic."""
    # Load settings from project directory
    settings_path = Path.cwd() / ".claude" / "settings.json"

    if not settings_path.exists():
        user_output("No hooks installed.")
        user_output("Total: 0 hook(s)")
        raise SystemExit(0)

    try:
        settings = load_settings(settings_path)
    except (json.JSONDecodeError, ValidationError) as e:
        user_output(f"Error loading settings.json: {e}")
        raise SystemExit(1) from None

    # Extract all hooks
    hooks = get_all_hooks(settings)

    if not hooks:
        user_output("No hooks installed.")
        user_output("Total: 0 hook(s)")
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
        user_output(f"{hook_spec} [{lifecycle} / {matcher}]")

    user_output(f"\nTotal: {len(hooks)} hook(s)")


@click.command(name="list")
def list_hooks() -> None:
    """List all installed hooks (alias: ls)."""
    _list_hooks_impl()


@click.command(name="ls", hidden=True)
def ls() -> None:
    """List all installed hooks (alias for list)."""
    _list_hooks_impl()
