"""Sync command for synchronizing installed kits with their sources."""

from pathlib import Path

import click

from dot_agent_kit.io import load_project_config, save_project_config
from dot_agent_kit.operations import check_for_updates, sync_all_kits, sync_kit
from dot_agent_kit.sources import BundledKitSource, KitResolver, StandalonePackageSource


@click.command()
@click.argument("kit-id", required=False)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed sync information",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force reinstall even if versions match",
)
def sync(kit_id: str | None, verbose: bool, force: bool) -> None:
    """Sync installed kits with their sources.

    This command updates one or all installed kits to their latest versions.
    Use 'install' for installing/updating a specific kit, and 'sync' for
    bulk update operations across all installed kits.

    Examples:
        # Sync all installed kits
        dot-agent kit sync

        # Sync a specific kit
        dot-agent kit sync github-workflows

        # Force sync all kits (reinstall even if up to date)
        dot-agent kit sync --force
    """
    project_dir = Path.cwd()

    config = load_project_config(project_dir)
    if config is None:
        click.echo("Error: No dot-agent.toml found", err=True)
        raise SystemExit(1)

    if len(config.kits) == 0:
        click.echo("No kits installed")
        return

    resolver = KitResolver(sources=[BundledKitSource(), StandalonePackageSource()])

    # Sync specific kit or all kits
    if kit_id is not None:
        if kit_id not in config.kits:
            click.echo(f"Error: Kit '{kit_id}' not installed", err=True)
            raise SystemExit(1)

        installed = config.kits[kit_id]
        check_result = check_for_updates(installed, resolver, force=force)

        if check_result.error_message:
            error_msg = f"Error: Failed to check for updates: {check_result.error_message}"
            click.echo(error_msg, err=True)
            raise SystemExit(1)

        if not check_result.has_update or check_result.resolved is None:
            click.echo(f"Kit '{kit_id}' is up to date")
            return

        result = sync_kit(kit_id, installed, check_result.resolved, project_dir, force=force)

        if result.was_updated:
            click.echo(f"✓ Updated {kit_id}: {result.old_version} → {result.new_version}")
            if verbose:
                click.echo(f"  Artifacts: {result.artifacts_updated}")

            # Save updated config
            if result.updated_kit is not None:
                updated_config = config.update_kit(result.updated_kit)
                save_project_config(project_dir, updated_config)

    else:
        # Sync all kits
        results = sync_all_kits(config, project_dir, resolver, force=force)

        updated_count = sum(1 for r in results if r.was_updated)

        if verbose or updated_count > 0:
            for result in results:
                if result.was_updated:
                    click.echo(f"✓ {result.kit_id}: {result.old_version} → {result.new_version}")
                elif verbose:
                    click.echo(f"  {result.kit_id}: up to date")

        # Save updated config if any kits were updated
        if updated_count > 0:
            updated_config = config
            for result in results:
                if result.was_updated and result.updated_kit is not None:
                    updated_config = updated_config.update_kit(result.updated_kit)
            save_project_config(project_dir, updated_config)

        if updated_count == 0:
            click.echo("All kits are up to date")
        else:
            click.echo(f"\nUpdated {updated_count} kit(s)")
