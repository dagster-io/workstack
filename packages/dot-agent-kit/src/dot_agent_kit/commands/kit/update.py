"""Update command for updating installed kits."""

from pathlib import Path

import click

from dot_agent_kit.io import (
    get_user_claude_dir,
    load_project_config,
    load_user_config,
    save_project_config,
    save_user_config,
)
from dot_agent_kit.operations import check_for_updates, sync_kit
from dot_agent_kit.sources import KitResolver, StandalonePackageSource


@click.command()
@click.argument("kit-id")
@click.option(
    "--user",
    "-u",
    "target",
    flag_value="user",
    help="Update kit in user directory (~/.claude)",
)
@click.option(
    "--project",
    "-p",
    "target",
    flag_value="project",
    default=True,
    help="Update kit in project directory (./.claude) [default]",
)
def update(kit_id: str, target: str) -> None:
    """Update an installed kit to the latest version.

    Examples:

        # Update kit in project directory
        dot-agent update github-workflows

        # Update kit in user directory
        dot-agent update productivity-kit --user
    """
    project_dir = Path.cwd()

    # Load appropriate config based on target
    if target == "user":
        config = load_user_config()
        location_name = "user directory (~/.claude)"
    else:
        loaded_config = load_project_config(project_dir)
        if loaded_config is None:
            click.echo("Error: No project configuration found", err=True)
            raise SystemExit(1)
        config = loaded_config
        location_name = "project directory (./.claude)"

    # Check if kit is installed in the target location
    if kit_id not in config.kits:
        click.echo(f"Error: Kit '{kit_id}' not installed in {location_name}", err=True)
        raise SystemExit(1)

    installed = config.kits[kit_id]

    # Check for updates
    resolver = KitResolver(sources=[StandalonePackageSource()])
    has_update, resolved = check_for_updates(installed, resolver)

    if not has_update or resolved is None:
        click.echo(f"Kit '{kit_id}' is already up to date (v{installed.version})")
        return

    # Perform sync (update)
    if target == "user":
        sync_dir = get_user_claude_dir()
    else:
        sync_dir = project_dir

    result = sync_kit(kit_id, installed, resolved, sync_dir)

    if result.was_updated:
        click.echo(f"✓ Updated {kit_id}: {result.old_version} → {result.new_version}")
        click.echo(f"  Artifacts updated: {result.artifacts_updated}")

        # Save updated config
        if result.updated_kit is not None:
            updated_config = config.update_kit(result.updated_kit)

            if target == "user":
                save_user_config(updated_config)
            else:
                save_project_config(project_dir, updated_config)
    else:
        click.echo(f"No changes made to {kit_id}")
