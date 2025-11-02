"""Remove command for uninstalling kits."""

from pathlib import Path

import click

from dot_agent_kit.hooks.installer import remove_hooks
from dot_agent_kit.io import (
    load_project_config,
    save_project_config,
)
from dot_agent_kit.models import ProjectConfig


@click.command()
@click.argument("kit-id")
def remove(kit_id: str) -> None:
    """Remove an installed kit.

    This removes all artifacts installed by the kit and updates the configuration.

    Examples:

        # Remove kit from project directory
        dot-agent remove github-workflows
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

    # Remove hooks if present (project-level only)
    hooks_removed = 0
    if target == "project" and installed.hooks:
        hooks_removed = remove_hooks(kit_id, project_dir)

    # Remove artifact files
    removed_count = 0
    failed_count = 0

    for artifact_path in installed.artifacts:
        artifact_file = project_dir / artifact_path
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
    save_project_config(project_dir, updated_config)

    # Show success message
    click.echo(f"✓ Removed {kit_id} v{installed.version}")
    click.echo(f"  Deleted {removed_count} artifact(s)")

    if hooks_removed > 0:
        click.echo(f"  Removed {hooks_removed} hook(s)")

    if failed_count > 0:
        click.echo(f"  Note: {failed_count} artifact(s) were already removed", err=True)
