"""Show artifact location command."""

from pathlib import Path

import click

from dot_agent_kit.services.unified_discovery import UnifiedArtifactDiscovery


@click.command("where")
@click.argument("name")
@click.option(
    "--type",
    "artifact_type",
    type=click.Choice(["skill", "command", "agent", "hook"], case_sensitive=False),
    help="Artifact type hint (helps with ambiguous names)",
)
def where(name: str, artifact_type: str | None) -> None:
    """Show the location of an artifact.

    Displays the absolute path(s) where the artifact is located.
    If the artifact exists at multiple levels, all locations are shown.
    """
    # Discover artifacts
    discovery = UnifiedArtifactDiscovery()
    result = discovery.discover_all()

    # Find matching artifacts
    all_artifacts = result.all_artifacts()
    matches = [a for a in all_artifacts if a.artifact_name == name]

    # Apply type filter if specified
    if artifact_type:
        matches = [a for a in matches if a.artifact_type == artifact_type]

    if not matches:
        click.echo(f"Error: No artifact found with name '{name}'", err=True)
        if artifact_type:
            click.echo(f"(searched for type: {artifact_type})", err=True)
        raise SystemExit(1)

    # Display locations
    if len(matches) == 1:
        artifact = matches[0]
        full_path = _get_full_path(artifact)
        click.echo(str(full_path))
    else:
        # Multiple matches - show all with context
        click.echo(f"Multiple locations found for '{name}':\n")
        for artifact in matches:
            full_path = _get_full_path(artifact)
            level_str = "user" if artifact.level and artifact.level.value == "user" else "project"
            click.echo(f"[{level_str}] {artifact.artifact_type}: {full_path}")


def _get_full_path(artifact) -> Path:
    """Get the full absolute path for an artifact."""
    if artifact.level and artifact.level.value == "user":
        base_path = Path.home() / ".claude"
    else:
        base_path = Path.cwd() / ".claude"

    return base_path / artifact.file_path
