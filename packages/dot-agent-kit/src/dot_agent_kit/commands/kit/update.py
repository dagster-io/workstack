"""Update command for updating installed kits to latest versions."""

from pathlib import Path

import click

from dot_agent_kit.io import load_project_config, save_project_config
from dot_agent_kit.operations import check_for_updates, sync_kit
from dot_agent_kit.sources import KitResolver, StandalonePackageSource


@click.command()
@click.argument("kit-id")
def update(kit_id: str) -> None:
    """Update an installed kit to the latest version.

    Examples:

        # Update kit in project directory
        dot-agent update github-workflows
    """
    project_dir = Path.cwd()

    # Load project config
    loaded_config = load_project_config(project_dir)
    if loaded_config is None:
        click.echo("Error: No project configuration found", err=True)
        raise SystemExit(1)
    config = loaded_config

    # Check if kit is installed
    if kit_id not in config.kits:
        click.echo(
            f"Error: Kit '{kit_id}' not installed in project directory (./.claude)", err=True
        )
        raise SystemExit(1)

    installed = config.kits[kit_id]

    # Check for updates
    resolver = KitResolver(sources=[StandalonePackageSource()])
    has_update, resolved = check_for_updates(installed, resolver)

    if not has_update or resolved is None:
        click.echo(f"Kit '{kit_id}' is already up to date (v{installed.version})")
        return

    # Perform sync (update)
    result = sync_kit(kit_id, installed, resolved, project_dir)

    if result.was_updated:
        click.echo(f"✓ Updated {kit_id}: {result.old_version} → {result.new_version}")
        click.echo(f"  Artifacts updated: {result.artifacts_updated}")

        # Save updated config
        if result.updated_kit is not None:
            updated_config = config.update_kit(result.updated_kit)
            save_project_config(project_dir, updated_config)
    else:
        click.echo(f"No changes made to {kit_id}")
