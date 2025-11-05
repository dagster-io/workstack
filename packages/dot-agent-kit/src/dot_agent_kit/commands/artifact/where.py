"""Artifact where command implementation."""

from pathlib import Path

import click

from dot_agent_kit.io.state import load_project_config
from dot_agent_kit.models.config import ProjectConfig
from dot_agent_kit.repositories.filesystem_artifact_repository import FilesystemArtifactRepository


@click.command(name="where")
@click.argument("name")
@click.option(
    "--type",
    "artifact_type",
    type=click.Choice(["skill", "command", "agent", "hook"]),
    help="Artifact type hint",
)
def where_artifact(name: str, artifact_type: str | None) -> None:
    """Show artifact filesystem location."""
    # Get paths
    user_path = Path.home() / ".claude"
    project_path = Path.cwd() / ".claude"

    # Load project config
    project_config = load_project_config(Path.cwd())
    if project_config is None:
        project_config = ProjectConfig(version="1", kits={})

    # Discover artifacts
    repository = FilesystemArtifactRepository()
    all_artifacts = repository.discover_multi_level(user_path, project_path, project_config)

    # Filter by name (case-insensitive)
    name_lower = name.lower()
    matching = [a for a in all_artifacts if a.artifact_name.lower() == name_lower]

    # Further filter by type if provided
    if artifact_type:
        matching = [a for a in matching if a.artifact_type == artifact_type]

    # Handle no matches
    if not matching:
        click.echo(f"No artifact found with name '{name}'", err=True)
        raise SystemExit(1)

    # Single match: output path only (shell-friendly)
    if len(matching) == 1:
        artifact = matching[0]
        if artifact.level.value == "user":
            base_dir = user_path
        else:
            base_dir = project_path

        full_path = base_dir / artifact.file_path

        # Check exists before resolve (LBYL)
        if full_path.exists():
            absolute_path = full_path.resolve()
            click.echo(str(absolute_path))
        else:
            click.echo(str(full_path))

    # Multiple matches: output with labels
    else:
        click.echo(f"Multiple locations found for '{name}':\n")

        for artifact in matching:
            if artifact.level.value == "user":
                base_dir = user_path
                level_label = "[user]"
            else:
                base_dir = project_path
                level_label = "[project]"

            full_path = base_dir / artifact.file_path

            # Check exists before resolve (LBYL)
            if full_path.exists():
                absolute_path = full_path.resolve()
            else:
                absolute_path = full_path

            click.echo(f"{level_label} {artifact.artifact_type}: {absolute_path}")
