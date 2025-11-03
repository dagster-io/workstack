"""List command for showing installed kits."""

from pathlib import Path

import click

from dot_agent_kit.io import load_project_config


@click.command(name="list")
def list_installed_kits() -> None:
    """List all installed kits in the current project."""
    project_dir = Path.cwd()
    loaded_config = load_project_config(project_dir)

    if loaded_config is None:
        click.echo("Error: No project configuration found", err=True)
        click.echo("Run this command from a project directory with a .claude/ folder", err=True)
        raise SystemExit(1)

    config = loaded_config

    if len(config.kits) == 0:
        click.echo("No kits installed")
        return

    # Display results
    click.echo(f"Installed {len(config.kits)} kit(s):\n")

    for kit_id, installed_kit in config.kits.items():
        line = (
            f"  {kit_id:<20} {installed_kit.version:<10} "
            f"{installed_kit.source:<15} {installed_kit.installed_at}"
        )
        click.echo(line)
