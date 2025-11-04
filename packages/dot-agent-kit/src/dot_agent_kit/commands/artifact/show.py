"""Show artifact content command."""

import click

from dot_agent_kit.models.artifact import InstalledArtifact
from dot_agent_kit.services.unified_discovery import UnifiedArtifactDiscovery


@click.command("show")
@click.argument("name")
@click.option(
    "--type",
    "artifact_type",
    type=click.Choice(["skill", "command", "agent", "hook"], case_sensitive=False),
    help="Artifact type hint (helps with ambiguous names)",
)
def show(name: str, artifact_type: str | None) -> None:
    """Display content of a specific artifact.

    Shows the full content of the artifact file along with metadata.
    If the artifact exists at multiple levels or multiple artifacts
    have the same name, you may need to use --type to disambiguate.
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

    if len(matches) > 1:
        click.echo(f"Error: Multiple artifacts found with name '{name}':", err=True)
        for artifact in matches:
            level_str = "user" if artifact.level and artifact.level.value == "user" else "project"
            click.echo(f"  - {artifact.artifact_type} at {level_str} level", err=True)
        click.echo("\nUse --type to specify which artifact to show", err=True)
        raise SystemExit(1)

    # Show the artifact
    artifact = matches[0]
    _display_artifact(artifact)


def _display_artifact(artifact: InstalledArtifact) -> None:
    """Display artifact content with metadata header."""
    # Display metadata header
    click.echo("─" * 70)
    click.echo(f"Artifact: {artifact.artifact_name}")
    click.echo(f"Type:     {artifact.artifact_type}")
    level_str = artifact.level.value if artifact.level else "unknown"
    click.echo(f"Level:    {level_str}")

    if artifact.source.value == "managed":
        click.echo(f"Source:   managed [{artifact.kit_id}@{artifact.kit_version}]")
    else:
        click.echo("Source:   local (manually created)")

    # Construct full path
    from pathlib import Path

    if artifact.level and artifact.level.value == "user":
        base_path = Path.home() / ".claude"
    else:
        base_path = Path.cwd() / ".claude"

    full_path = base_path / artifact.file_path
    click.echo(f"Path:     {full_path}")

    # Type-specific metadata
    if artifact.artifact_type == "hook":
        if artifact.settings_source:
            settings_warning = ""
            if artifact.settings_source in ["settings.local.json", "orphaned"]:
                settings_warning = " ⚠️"
            click.echo(f"Settings: {artifact.settings_source}{settings_warning}")

        if artifact.lifecycle:
            click.echo(f"Lifecycle: {artifact.lifecycle}")

        if artifact.matcher:
            click.echo(f"Matcher:   {artifact.matcher}")

        if artifact.timeout:
            click.echo(f"Timeout:   {artifact.timeout}s")

    click.echo("─" * 70)
    click.echo()

    # Display content
    if full_path.exists():
        content = full_path.read_text(encoding="utf-8")
        click.echo(content)
    else:
        click.echo(f"Warning: File not found at {full_path}", err=True)
        click.echo("The artifact may have been deleted or moved.", err=True)
