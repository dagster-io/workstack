"""Status command for showing installed kits."""

from pathlib import Path

import click

from dot_agent_kit.io import discover_installed_artifacts, load_project_config

# Reusable option decorator
verbose_option = click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed installation information",
)


def _show_status(verbose: bool) -> None:
    """Implementation of status display logic."""
    project_dir = Path.cwd()

    # Load project config for managed kits
    project_config = load_project_config(project_dir)

    if project_config is None:
        msg = "Error: No dot-agent.toml found. Run 'dot-agent kit init' to create one."
        click.echo(msg, err=True)
        raise SystemExit(1)

    # Discover artifacts in filesystem
    discovered = discover_installed_artifacts(project_dir, project_config)

    # Determine managed vs unmanaged
    managed_kits = set(project_config.kits.keys()) if project_config else set()
    all_installed = set(discovered.keys())
    unmanaged_kits = all_installed - managed_kits

    # Display managed kits section
    click.echo("Managed Kits:")
    if managed_kits and project_config:
        for kit_id in sorted(managed_kits):
            kit = project_config.kits[kit_id]
            click.echo(f"  {kit_id} v{kit.version} ({kit.source})")
            if verbose:
                artifact_types = discovered.get(kit_id, set())
                if artifact_types:
                    types_str = ", ".join(sorted(artifact_types))
                    click.echo(f"    Artifacts: {types_str}")
                click.echo(f"    Installed: {kit.installed_at}")
    else:
        click.echo("  (none)")

    click.echo()

    # Display unmanaged artifacts section
    click.echo("Unmanaged Artifacts:")
    if unmanaged_kits:
        for kit_id in sorted(unmanaged_kits):
            artifact_types = discovered[kit_id]
            types_str = ", ".join(sorted(artifact_types))
            click.echo(f"  {kit_id} ({types_str})")
    else:
        click.echo("  (none)")


@click.command()
@verbose_option
def status(verbose: bool) -> None:
    """Show status of kits and artifacts (alias: st).

    Displays managed kits (tracked in config) and unmanaged artifacts
    (present in .claude/ but not tracked).
    """
    _show_status(verbose)


@click.command(name="st", hidden=True)
@verbose_option
def st(verbose: bool) -> None:
    """Show status of kits and artifacts (alias for status)."""
    _show_status(verbose)
