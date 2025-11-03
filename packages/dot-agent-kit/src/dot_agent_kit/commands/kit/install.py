"""Install command for installing or updating kits."""

from dataclasses import replace
from pathlib import Path

import click

from dot_agent_kit.hooks.installer import install_hooks, remove_hooks
from dot_agent_kit.io import (
    create_default_config,
    load_kit_manifest,
    load_project_config,
    save_project_config,
)
from dot_agent_kit.operations import (
    check_for_updates,
    get_installation_context,
    install_kit_to_project,
    sync_kit,
)
from dot_agent_kit.sources import BundledKitSource, KitResolver, StandalonePackageSource


@click.command()
@click.argument("kit-id")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force reinstall even if already up to date",
)
def install(kit_id: str, force: bool) -> None:
    """Install a kit or update it if already installed.

    This command is idempotent - it will install the kit if not present,
    or update it to the latest version if already installed.

    Examples:

        # Install or update a kit
        dot-agent kit install github-workflows

        # Force reinstall a kit
        dot-agent kit install github-workflows --force
    """

    # Get installation context
    project_dir = Path.cwd()
    context = get_installation_context(project_dir)

    # Load project config
    loaded_config = load_project_config(project_dir)
    if loaded_config is None:
        config = create_default_config()
    else:
        config = loaded_config

    # Resolve kit source (use both bundled and package sources)
    resolver = KitResolver(sources=[BundledKitSource(), StandalonePackageSource()])

    # Check if kit already installed - if so, update it
    if kit_id in config.kits:
        installed = config.kits[kit_id]
        has_update, resolved = check_for_updates(installed, resolver, force=force)

        if not has_update or resolved is None:
            if not force:
                click.echo(f"Kit '{kit_id}' is already up to date (v{installed.version})")
                return
            else:
                # Force reinstall even if up to date
                resolved = resolver.resolve(kit_id)
                if resolved is None:
                    click.echo(f"Error: Kit '{kit_id}' not found", err=True)
                    raise SystemExit(1)

        # Update the kit using sync
        click.echo(f"Updating {kit_id} to v{resolved.version}...")
        result = sync_kit(kit_id, installed, resolved, project_dir, force=force)

        if result.was_updated:
            click.echo(f"✓ Updated {kit_id}: {result.old_version} → {result.new_version}")
            click.echo(f"  Artifacts: {result.artifacts_updated}")

            # Handle hooks: remove old and install new
            manifest = load_kit_manifest(resolved.manifest_path)
            hooks_count = 0

            # Remove old hooks
            remove_hooks(kit_id, project_dir)

            # Install new hooks if present
            if manifest.hooks:
                hooks_count = install_hooks(
                    kit_id=manifest.name,
                    hooks=manifest.hooks,
                    kit_path=resolved.artifacts_base,
                    project_root=project_dir,
                )

            # Save updated config with new hooks
            if result.updated_kit is not None:
                updated_kit = result.updated_kit
                if manifest.hooks:
                    updated_kit = replace(updated_kit, hooks=manifest.hooks)
                updated_config = config.update_kit(updated_kit)
                save_project_config(project_dir, updated_config)

                if hooks_count > 0:
                    click.echo(f"  Installed {hooks_count} hook(s)")
        else:
            click.echo(f"Kit '{kit_id}' was already up to date")

        return

    # Kit not installed - do fresh install
    resolved = resolver.resolve(kit_id)
    if resolved is None:
        click.echo(f"Error: Kit '{kit_id}' not found", err=True)
        raise SystemExit(1)

    # Load manifest
    manifest = load_kit_manifest(resolved.manifest_path)

    # Install the kit (always install complete kit, no artifact selection)
    click.echo(f"Installing {kit_id} v{resolved.version} to {context.get_claude_dir()}...")

    installed_kit = install_kit_to_project(
        resolved,
        context,
        overwrite=force,  # Use force flag for overwrite
        filtered_artifacts=None,  # Always install all artifacts
    )

    # Install hooks if present
    hooks_count = 0
    if manifest.hooks:
        hooks_count = install_hooks(
            kit_id=manifest.name,
            hooks=manifest.hooks,
            kit_path=resolved.artifacts_base,
            project_root=project_dir,
        )
        # Update installed kit with hooks
        installed_kit = replace(installed_kit, hooks=manifest.hooks)

    # Update config
    updated_config = config.update_kit(installed_kit)
    save_project_config(project_dir, updated_config)

    # Show success message
    artifact_count = len(installed_kit.artifacts)
    click.echo(f"✓ Installed {kit_id} v{installed_kit.version} ({artifact_count} artifacts)")

    if hooks_count > 0:
        click.echo(f"  Installed {hooks_count} hook(s)")

    click.echo(f"  Location: {context.get_claude_dir()}")
