"""Install command for installing kits."""

from pathlib import Path

import click

from dot_agent_kit.io import (
    create_default_config,
    load_kit_manifest,
    load_project_config,
    load_user_config,
    save_project_config,
    save_user_config,
)
from dot_agent_kit.models import ConflictPolicy, InstallationTarget
from dot_agent_kit.operations import (
    ArtifactSpec,
    get_installation_context,
    install_kit_to_target,
)
from dot_agent_kit.sources import KitResolver, StandalonePackageSource


@click.command()
@click.argument("kit-spec")
@click.option(
    "--user",
    "-u",
    "target",
    flag_value="user",
    help="Install to user directory (~/.claude)",
)
@click.option(
    "--project",
    "-p",
    "target",
    flag_value="project",
    default=True,
    help="Install to project directory (./.claude) [default]",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing artifacts",
)
def install(kit_spec: str, target: str, force: bool) -> None:
    """Install a kit or specific artifacts from a kit.

    Examples:

        # Install entire kit to project
        dot-agent kit install github-workflows

        # Install specific artifact to project
        dot-agent kit install github-workflows:pr-review

        # Install multiple artifacts to project
        dot-agent kit install github-workflows:pr-review,auto-merge

        # Install to user directory
        dot-agent kit install productivity-kit --user

        # Install specific artifact to user directory
        dot-agent kit install code-review:style-checker --user
    """
    # Parse kit spec to extract kit ID and artifact selection
    artifact_spec = ArtifactSpec(kit_spec)
    kit_id = artifact_spec.get_kit_id()

    # Determine installation target
    install_target = InstallationTarget.USER if target == "user" else InstallationTarget.PROJECT

    # Get installation context
    project_dir = Path.cwd()
    context = get_installation_context(install_target, project_dir)

    # Load appropriate config
    if install_target == InstallationTarget.USER:
        config = load_user_config()
    else:
        loaded_config = load_project_config(project_dir)
        if loaded_config is None:
            config = create_default_config()
        else:
            config = loaded_config

    # Check if kit already installed
    if kit_id in config.kits:
        if not force:
            click.echo(
                f"Error: Kit '{kit_id}' is already installed at {context.get_claude_dir()}\n"
                f"Use --force to overwrite",
                err=True,
            )
            raise SystemExit(1)

    # Resolve kit source
    resolver = KitResolver(sources=[StandalonePackageSource()])
    resolved = resolver.resolve(kit_id)

    if resolved is None:
        click.echo(f"Error: Kit '{kit_id}' not found", err=True)
        raise SystemExit(1)

    # Load manifest to filter artifacts
    manifest = load_kit_manifest(resolved.manifest_path)

    # Filter artifacts based on spec
    filtered_artifacts = artifact_spec.filter_artifacts(manifest)

    # Determine conflict policy
    conflict_policy = ConflictPolicy.OVERWRITE if force else ConflictPolicy.ERROR

    # Install the kit
    click.echo(f"Installing {kit_id} to {context.get_claude_dir()}...")

    installed_kit = install_kit_to_target(
        resolved,
        context,
        conflict_policy,
        filtered_artifacts,
    )

    # Update config
    updated_config = config.update_kit(installed_kit)

    if install_target == InstallationTarget.USER:
        save_user_config(updated_config)
    else:
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

    click.echo(f"  Location: {context.get_claude_dir()}")
