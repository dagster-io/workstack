"""List artifacts command."""

import click

from dot_agent_kit.models.artifact import ArtifactLevel
from dot_agent_kit.services.unified_discovery import UnifiedArtifactDiscovery


@click.command("list")
@click.option(
    "--user",
    "level_filter",
    flag_value="user",
    help="Show only user-level artifacts (~/.claude/)",
)
@click.option(
    "--project",
    "level_filter",
    flag_value="project",
    help="Show only project-level artifacts (./.claude/)",
)
@click.option(
    "--all",
    "level_filter",
    flag_value="all",
    default=True,
    help="Show artifacts from both levels (default)",
)
@click.option(
    "--type",
    "artifact_type",
    type=click.Choice(["skill", "command", "agent", "hook"], case_sensitive=False),
    help="Filter by artifact type",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show detailed information",
)
def list_cmd(
    level_filter: str,
    artifact_type: str | None,
    verbose: bool,
) -> None:
    """List installed Claude artifacts.

    By default, shows artifacts from both user and project levels.
    Use --user or --project to filter by level.
    """
    # Determine level filter
    level: ArtifactLevel | None = None
    if level_filter == "user":
        level = ArtifactLevel.USER
    elif level_filter == "project":
        level = ArtifactLevel.PROJECT

    # Discover artifacts
    discovery = UnifiedArtifactDiscovery()

    if level is None and artifact_type is None:
        # No filters - get all
        result = discovery.discover_all()
        artifacts = result.all_artifacts()
    else:
        # Apply filters
        artifacts = discovery.discover_with_filters(
            artifact_type=artifact_type,
            level=level,
        )

    # Display results
    if not artifacts:
        click.echo("No artifacts found.")
        return

    if verbose:
        _display_verbose(artifacts)
    else:
        _display_compact(artifacts)


def _display_compact(artifacts: list) -> None:
    """Display artifacts in compact format."""
    from collections import defaultdict

    # Group by type
    by_type: dict[str, list] = defaultdict(list)
    for artifact in artifacts:
        by_type[artifact.artifact_type].append(artifact)

    click.echo("Claude Artifacts\n")

    for artifact_type in sorted(by_type.keys()):
        items = by_type[artifact_type]
        # Capitalize and pluralize type name
        type_name = artifact_type.capitalize() + "s"
        click.echo(f"{type_name} ({len(items)})")

        for artifact in sorted(items, key=lambda a: a.artifact_name):
            # Level indicator
            level_indicator = "[U]" if artifact.level == ArtifactLevel.USER else "[P]"

            # Source indicator
            if artifact.source.value == "managed":
                source = f"[{artifact.kit_id}@{artifact.kit_version}]"
            else:
                source = "[local]"

            click.echo(f"  {level_indicator} {artifact.artifact_name:30} {source}")

        click.echo()  # Blank line between types

    click.echo("Use -v for detailed information or 'dot-agent artifact show <name>'")


def _display_verbose(artifacts: list) -> None:
    """Display artifacts in verbose format."""
    from collections import defaultdict

    # Group by type
    by_type: dict[str, list] = defaultdict(list)
    for artifact in artifacts:
        by_type[artifact.artifact_type].append(artifact)

    click.echo("═" * 70)
    click.echo("CLAUDE ARTIFACTS - Project & User Levels")
    click.echo("═" * 70)
    click.echo()

    for artifact_type in sorted(by_type.keys()):
        items = by_type[artifact_type]
        type_name = artifact_type.upper() + "S"
        click.echo(f"{type_name} ({len(items)} total)")
        click.echo("─" * 70)

        for artifact in sorted(items, key=lambda a: a.artifact_name):
            # Level indicator
            level_indicator = "[U]" if artifact.level == ArtifactLevel.USER else "[P]"

            click.echo(f"{level_indicator} {artifact.artifact_name}")

            # Source
            if artifact.source.value == "managed":
                source_str = f"managed [{artifact.kit_id}@{artifact.kit_version}]"
            else:
                source_str = "local (manually created)"
            click.echo(f"    Source:       {source_str}")

            # Path
            click.echo(f"    Path:         {artifact.file_path}")

            # Type-specific metadata
            if artifact.artifact_type == "hook":
                if artifact.settings_source:
                    settings_warning = ""
                    if artifact.settings_source == "settings.local.json":
                        settings_warning = " ⚠️"
                    elif artifact.settings_source == "orphaned":
                        settings_warning = " ⚠️"
                    click.echo(f"    Settings:     {artifact.settings_source}{settings_warning}")

                if artifact.lifecycle:
                    click.echo(f"    Lifecycle:    {artifact.lifecycle}")

                if artifact.matcher:
                    click.echo(f"    Matcher:      {artifact.matcher}")

                if artifact.timeout:
                    click.echo(f"    Timeout:      {artifact.timeout}s")

            click.echo()  # Blank line between artifacts

        click.echo()  # Blank line between types

    click.echo("═" * 70)
    click.echo("Legend: [U]=User level  [P]=Project level  ⚠️=Needs attention")
    click.echo("Use 'dot-agent artifact show <name>' for detailed content")
    click.echo("═" * 70)
