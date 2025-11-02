"""Init command for installing kits."""

from pathlib import Path

import click

from dot_agent_kit.io import (
    create_default_config,
    load_project_config,
    save_project_config,
)
from dot_agent_kit.models import ProjectConfig
from dot_agent_kit.operations.install import install_kit
from dot_agent_kit.sources import BundledKitSource, KitResolver, StandalonePackageSource


@click.command()
@click.argument("package")
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing artifacts",
)
def init(package: str, force: bool) -> None:
    """Initialize and install a kit from bundled data or Python package."""
    project_dir = Path.cwd()

    # Load or create project config
    config = load_project_config(project_dir)
    if config is None:
        config = create_default_config()

    # Resolve the kit (try bundled kits first, then standalone packages)
    resolver = KitResolver(sources=[BundledKitSource(), StandalonePackageSource()])

    try:
        resolved = resolver.resolve(package)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e

    # Check if already installed
    if resolved.kit_id in config.kits:
        click.echo(f"Error: Kit '{resolved.kit_id}' is already installed", err=True)
        raise SystemExit(1)

    # Determine conflict policy
    conflict_policy = config.default_conflict_policy
    if force:
        conflict_policy = "overwrite"

    # Install the kit
    try:
        installed_kit = install_kit(resolved, project_dir, conflict_policy)
    except FileExistsError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e

    # Update project config
    new_kits = {**config.kits, resolved.kit_id: installed_kit}
    updated_config = ProjectConfig(
        version=config.version,
        default_conflict_policy=config.default_conflict_policy,
        kits=new_kits,
    )

    save_project_config(project_dir, updated_config)

    click.echo(f"✓ Installed kit: {resolved.kit_id} v{installed_kit.version}")
    click.echo(f"  Artifacts: {len(installed_kit.artifacts)}")
