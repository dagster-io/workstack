"""List command for showing installed kits."""

from pathlib import Path

import click

from dot_agent_kit.io import load_project_config


@click.command("list")
def list_kits() -> None:
    """List all installed kits."""
    project_dir = Path.cwd()
    config = load_project_config(project_dir)

    if config is None or len(config.kits) == 0:
        click.echo("No kits installed")
        return

    click.echo("Installed Kits:")
    for kit_id, kit in sorted(config.kits.items()):
        click.echo(f"  {kit_id}")
        click.echo(f"    Version: {kit.version}")
        click.echo(f"    Source: {kit.source}")
        click.echo(f"    Installed: {kit.installed_at}")
        click.echo(f"    Artifacts: {len(kit.artifacts)}")
        click.echo()
