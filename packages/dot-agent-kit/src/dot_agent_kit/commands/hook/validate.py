"""Validate command for checking hooks configuration."""

import json
from pathlib import Path

import click
from pydantic import ValidationError

from dot_agent_kit.hooks.models import ClaudeSettings


@click.command(name="validate")
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
