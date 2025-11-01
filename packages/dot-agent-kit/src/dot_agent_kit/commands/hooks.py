"""Hook management commands."""

from pathlib import Path

import click

from dot_agent_kit.io import (
    get_user_claude_dir,
    load_hook_manifest,
    update_hook_enabled,
)


def parse_hook_path(hook_path: str, hooks_dir: Path) -> Path:
    """Parse and validate hook path, returning path to hooks.toml.

    Args:
        hook_path: Hook path in format "kit-name/hook-name"
        hooks_dir: Path to hooks directory

    Returns:
        Path to the kit's hooks.toml file

    Raises:
        SystemExit: If path format is invalid or kit not found
    """
    parts = hook_path.split("/")
    if len(parts) != 2:
        click.echo(
            "Error: Invalid hook path format. Use: kit-name/hook-name",
            err=True,
        )
        raise SystemExit(1)

    kit_name, _hook_name = parts
    hooks_toml = hooks_dir / kit_name / "hooks.toml"

    if not hooks_toml.exists():
        click.echo(f"Error: Kit '{kit_name}' not found or has no hooks", err=True)
        raise SystemExit(1)

    return hooks_toml


@click.group()
def hooks() -> None:
    """Manage installed hooks."""


@hooks.command("list")
def list_hooks() -> None:
    """List all installed hooks."""
    claude_dir = get_user_claude_dir()
    hooks_dir = claude_dir / ".dot-agent" / "hooks"

    if not hooks_dir.exists():
        click.echo("No hooks installed")
        return

    # Scan for kit hook directories
    kit_dirs = [d for d in hooks_dir.iterdir() if d.is_dir()]

    if not kit_dirs:
        click.echo("No hooks installed")
        return

    # Display hooks grouped by kit
    total_hooks = 0
    enabled_hooks = 0

    for kit_dir in sorted(kit_dirs):
        hooks_toml = kit_dir / "hooks.toml"
        if not hooks_toml.exists():
            continue

        manifest = load_hook_manifest(hooks_toml)
        click.echo(f"\n{manifest.kit_id} (v{manifest.kit_version})")

        for hook in manifest.hooks:
            total_hooks += 1
            if hook.enabled:
                enabled_hooks += 1

            status = "✓" if hook.enabled else "✗"
            status_text = (
                click.style("enabled", fg="green")
                if hook.enabled
                else click.style("disabled", fg="red")
            )

            click.echo(f"  {status} {hook.name} [{status_text}]")
            click.echo(f"      Lifecycle: {hook.lifecycle}")
            click.echo(f"      Matcher:   {hook.matcher or '(always)'}")
            if hook.description:
                click.echo(f"      {hook.description}")

    disabled_count = total_hooks - enabled_hooks
    click.echo(f"\nTotal: {total_hooks} hooks ({enabled_hooks} enabled, {disabled_count} disabled)")


@hooks.command("enable")
@click.argument("hook_path")
def enable_hook(hook_path: str) -> None:
    """Enable a specific hook.

    HOOK_PATH format: kit-name/hook-name

    Example:
        dot-agent hooks enable my-kit/my-hook
    """
    claude_dir = get_user_claude_dir()
    hooks_dir = claude_dir / ".dot-agent" / "hooks"

    hooks_toml = parse_hook_path(hook_path, hooks_dir)
    hook_name = hook_path.split("/")[1]

    try:
        update_hook_enabled(hooks_toml, hook_name, enabled=True)
        click.echo(f"✓ Enabled hook: {hook_path}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e


@hooks.command("disable")
@click.argument("hook_path")
def disable_hook(hook_path: str) -> None:
    """Disable a specific hook.

    HOOK_PATH format: kit-name/hook-name

    Example:
        dot-agent hooks disable my-kit/my-hook
    """
    claude_dir = get_user_claude_dir()
    hooks_dir = claude_dir / ".dot-agent" / "hooks"

    hooks_toml = parse_hook_path(hook_path, hooks_dir)
    hook_name = hook_path.split("/")[1]

    try:
        update_hook_enabled(hooks_toml, hook_name, enabled=False)
        click.echo(f"✓ Disabled hook: {hook_path}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e
