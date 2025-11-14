"""Status command for showing installed kits."""

from pathlib import Path

import click

from dot_agent_kit.cli.output import user_output
from dot_agent_kit.io import discover_installed_artifacts, require_project_config

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
    project_config = require_project_config(project_dir)

    # Discover artifacts in filesystem
    discovered = discover_installed_artifacts(project_dir, project_config)

    # Determine managed vs unmanaged
    managed_kits = set(project_config.kits.keys()) if project_config else set()
    all_installed = set(discovered.keys())
    unmanaged_kits = all_installed - managed_kits

    # Display managed kits section
    user_output("Managed Kits:")
    if managed_kits and project_config:
        for kit_id in sorted(managed_kits):
            kit = project_config.kits[kit_id]
            user_output(f"  {kit_id} v{kit.version} ({kit.source_type})")
            if verbose:
                artifact_types = discovered.get(kit_id, set())
                if artifact_types:
                    types_str = ", ".join(sorted(artifact_types))
                    user_output(f"    Artifacts: {types_str}")
    else:
        user_output("  (none)")

    user_output()

    # Display unmanaged artifacts section
    user_output("Unmanaged Artifacts:")
    if unmanaged_kits:
        for kit_id in sorted(unmanaged_kits):
            artifact_types = discovered[kit_id]
            types_str = ", ".join(sorted(artifact_types))
            user_output(f"  {kit_id} ({types_str})")
    else:
        user_output("  (none)")

    user_output("\nUse 'dot-agent artifact list' for detailed artifact inspection")


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
