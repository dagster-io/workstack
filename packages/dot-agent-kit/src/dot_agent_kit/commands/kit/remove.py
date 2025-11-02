"""Remove command for uninstalling kits."""

from pathlib import Path

import click

from dot_agent_kit.io import (
    get_user_claude_dir,
    load_project_config,
    load_user_config,
    save_project_config,
    save_user_config,
)
from dot_agent_kit.models import ProjectConfig


@click.command()
@click.argument("kit-id")
@click.option(
    "--user",
    "-u",
    "target",
    flag_value="user",
    help="Remove kit from user directory (~/.claude)",
)
@click.option(
    "--project",
    "-p",
    "target",
    flag_value="project",
    default=True,
    help="Remove kit from project directory (./.claude) [default]",
)
def remove(kit_id: str, target: str) -> None:
    """Remove an installed kit.

    This removes all artifacts installed by the kit and updates the configuration.

    Examples:

        # Remove kit from project directory
        dot-agent remove github-workflows

        # Remove kit from user directory
        dot-agent remove productivity-kit --user
    """
    project_dir = Path.cwd()

    # Load appropriate config based on target
    if target == "user":
        config = load_user_config()
        base_dir = get_user_claude_dir()
        location_name = "user directory (~/.claude)"
    else:
        loaded_config = load_project_config(project_dir)
        if loaded_config is None:
            click.echo("Error: No project configuration found", err=True)
            raise SystemExit(1)
        config = loaded_config
        base_dir = project_dir
        location_name = "project directory (./.claude)"

    # Check if kit is installed in the target location
    if kit_id not in config.kits:
        click.echo(f"Error: Kit '{kit_id}' not installed in {location_name}", err=True)
        raise SystemExit(1)

    installed = config.kits[kit_id]

    # Remove artifact files
    removed_count = 0
    failed_count = 0

    for artifact_path in installed.artifacts:
        artifact_file = base_dir / artifact_path
        if artifact_file.exists():
            artifact_file.unlink()
            removed_count += 1
        else:
            # File already removed or doesn't exist
            failed_count += 1

    # Remove kit from config
    new_kits = {k: v for k, v in config.kits.items() if k != kit_id}
    updated_config = ProjectConfig(
        version=config.version,
        default_conflict_policy=config.default_conflict_policy,
        kits=new_kits,
    )

    # Save updated config
    if target == "user":
        save_user_config(updated_config)
    else:
        save_project_config(project_dir, updated_config)

    # Show success message
    click.echo(f"✓ Removed {kit_id} v{installed.version}")
    click.echo(f"  Deleted {removed_count} artifact(s)")

    if failed_count > 0:
        click.echo(f"  Note: {failed_count} artifact(s) were already removed", err=True)
