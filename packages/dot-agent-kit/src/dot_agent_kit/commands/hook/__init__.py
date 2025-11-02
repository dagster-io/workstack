"""Hook management CLI commands."""

import json
from pathlib import Path

import click
from pydantic import ValidationError

from dot_agent_kit.hooks.models import ClaudeSettings
from dot_agent_kit.hooks.settings import get_all_hooks, load_settings


@click.group(name="hook")
def hook_group() -> None:
    """Manage Claude Code hooks."""


@hook_group.command(name="list")
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
        hook_spec = f"{entry.dot_agent.kit_id}:{entry.dot_agent.hook_id}"
        click.echo(f"{hook_spec} [{lifecycle} / {matcher}]", err=False)

    click.echo(f"Total: {len(hooks)} hook(s)", err=False)


@hook_group.command(name="show")
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
        if entry.dot_agent.kit_id == kit_id and entry.dot_agent.hook_id == hook_id:
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


@hook_group.command(name="validate")
def validate_hooks() -> None:
    """Validate hooks configuration in settings.json."""
    settings_path = Path.cwd() / ".claude" / "settings.json"

    if not settings_path.exists():
        click.echo("✓ No settings.json file (valid - no hooks configured)", err=False)
        raise SystemExit(0)

    # Try to load and validate
    try:
        content = settings_path.read_text(encoding="utf-8")
        data = json.loads(content)
        ClaudeSettings.model_validate(data)
        click.echo("✓ Hooks configuration is valid", err=False)
        raise SystemExit(0)
    except json.JSONDecodeError as e:
        click.echo(f"✗ Invalid JSON in settings.json: {e}", err=True)
        raise SystemExit(1) from None
    except ValidationError as e:
        click.echo("✗ Validation errors in settings.json:", err=True)
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            msg = error["msg"]
            click.echo(f"  {loc}: {msg}", err=True)
        raise SystemExit(1) from None
