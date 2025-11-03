"""Install command for installing kits and artifacts."""

from dataclasses import replace
from pathlib import Path

import click

from dot_agent_kit.hooks.installer import install_hooks
from dot_agent_kit.io import (
    create_default_config,
    load_kit_manifest,
    load_project_config,
    save_project_config,
)
from dot_agent_kit.operations import (
    ArtifactSpec,
    get_installation_context,
    install_kit_to_project,
)
from dot_agent_kit.sources import BundledKitSource, KitResolver, StandalonePackageSource


@click.command()
@click.argument("kit-spec")
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing artifacts",
)
def install(kit_spec: str, overwrite: bool) -> None:
    """Install a kit or specific artifacts from a kit.

    Examples:

        # Install entire kit to project
        dot-agent install github-workflows

        # Install specific artifact to project
        dot-agent install github-workflows:pr-review

        # Install multiple artifacts to project
        dot-agent install github-workflows:pr-review,auto-merge
    """
    # Parse kit spec to extract kit ID and artifact selection
    artifact_spec = ArtifactSpec(kit_spec)
    kit_id = artifact_spec.get_kit_id()

    # Get installation context
    project_dir = Path.cwd()
    context = get_installation_context(project_dir)

    # Load project config
    loaded_config = load_project_config(project_dir)
    if loaded_config is None:
        config = create_default_config()
    else:
        config = loaded_config

    # Check if kit already installed
    if kit_id in config.kits:
        if not overwrite:
            click.echo(
                f"Error: Kit '{kit_id}' is already installed at {context.get_claude_dir()}\n"
                f"Use --overwrite to overwrite",
                err=True,
            )
            raise SystemExit(1)

    # Resolve kit source
    resolver = KitResolver(sources=[BundledKitSource(), StandalonePackageSource()])
    resolved = resolver.resolve(kit_id)

    if resolved is None:
        click.echo(f"Error: Kit '{kit_id}' not found", err=True)
        raise SystemExit(1)

    # Load manifest to filter artifacts
    manifest = load_kit_manifest(resolved.manifest_path)

    # Filter artifacts based on spec
    filtered_artifacts = artifact_spec.filter_artifacts(manifest)

    # Install the kit
    click.echo(f"Installing {kit_id} to {context.get_claude_dir()}...")

    installed_kit = install_kit_to_project(
        resolved,
        context,
        overwrite,
        filtered_artifacts,
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
    artifact_names = artifact_spec.get_artifact_names()

    if artifact_names:
        click.echo(
            f"✓ Installed {len(artifact_names)} artifact(s) from {kit_id} v{installed_kit.version}"
        )
    else:
        click.echo(f"✓ Installed {kit_id} v{installed_kit.version} ({artifact_count} artifacts)")

    if hooks_count > 0:
        click.echo(f"  Installed {hooks_count} hook(s)")

    click.echo(f"  Location: {context.get_claude_dir()}")
