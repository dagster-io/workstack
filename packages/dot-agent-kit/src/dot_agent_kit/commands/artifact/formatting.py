"""Formatting functions for artifact display output."""

import click

from dot_agent_kit.models.artifact import ArtifactLevel, ArtifactSource, InstalledArtifact


def format_level_indicator(level: ArtifactLevel) -> str:
    """Format level indicator for artifact display.

    Args:
        level: Artifact installation level

    Returns:
        Formatted indicator string: [U] for user, [P] for project
    """
    if level == ArtifactLevel.USER:
        return click.style("[U]", fg="blue", bold=True)
    return click.style("[P]", fg="green", bold=True)


def format_source_indicator(artifact: InstalledArtifact) -> str:
    """Format source indicator for artifact display.

    Args:
        artifact: Artifact to format source for

    Returns:
        Formatted source string: [kit-name@version] or [local]
    """
    if artifact.source == ArtifactSource.MANAGED:
        if artifact.kit_id and artifact.kit_version:
            return click.style(f"[{artifact.kit_id}@{artifact.kit_version}]", fg="cyan")
        return click.style("[managed]", fg="cyan")
    return click.style("[local]", fg="yellow")


def format_compact_artifact_line(artifact: InstalledArtifact) -> str:
    """Format single-line compact representation of artifact.

    Args:
        artifact: Artifact to format

    Returns:
        Formatted line: [level] name [source]
    """
    level = format_level_indicator(artifact.level)
    source = format_source_indicator(artifact)
    name = click.style(artifact.artifact_name, bold=True)
    return f"{level} {name} {source}"


def format_artifact_header(artifact: InstalledArtifact) -> str:
    """Format metadata header for artifact show command.

    Args:
        artifact: Artifact to format header for

    Returns:
        Multi-line formatted header with metadata
    """
    lines = []
    lines.append(click.style(f"Artifact: {artifact.artifact_name}", bold=True, fg="white"))
    lines.append(f"Type: {artifact.artifact_type}")
    lines.append(f"Level: {artifact.level.value}")
    lines.append(f"Source: {artifact.source.value}")

    if artifact.kit_id:
        lines.append(f"Kit: {artifact.kit_id}")
    if artifact.kit_version:
        lines.append(f"Version: {artifact.kit_version}")

    lines.append(f"Path: {artifact.file_path}")

    return "\n".join(lines)


def format_hook_metadata(artifact: InstalledArtifact) -> str:
    """Format hook-specific metadata.

    Args:
        artifact: Hook artifact to format metadata for

    Returns:
        Formatted hook metadata string with settings source
    """
    if artifact.artifact_type != "hook":
        return ""

    lines = []

    if artifact.settings_source:
        if artifact.settings_source == "settings.local.json":
            warning = click.style("⚠️", fg="yellow")
            lines.append(f"Settings: {artifact.settings_source} {warning}")
        else:
            lines.append(f"Settings: {artifact.settings_source}")

    return "\n".join(lines) if lines else ""


def format_compact_list(artifacts: list[InstalledArtifact]) -> str:
    """Format compact view grouped by type.

    Args:
        artifacts: List of artifacts to format

    Returns:
        Formatted compact list grouped by artifact type
    """
    if not artifacts:
        return ""

    # Group by type
    by_type: dict[str, list[InstalledArtifact]] = {}
    for artifact in artifacts:
        if artifact.artifact_type not in by_type:
            by_type[artifact.artifact_type] = []
        by_type[artifact.artifact_type].append(artifact)

    # Format each group
    lines = []
    for artifact_type in ["skill", "command", "agent", "hook"]:
        if artifact_type not in by_type:
            continue

        type_artifacts = by_type[artifact_type]
        lines.append(click.style(f"\n{artifact_type.capitalize()}s:", bold=True, fg="white"))

        for artifact in sorted(type_artifacts, key=lambda a: a.artifact_name):
            lines.append(f"  {format_compact_artifact_line(artifact)}")

    return "\n".join(lines)


def format_verbose_list(artifacts: list[InstalledArtifact]) -> str:
    """Format detailed view with metadata.

    Args:
        artifacts: List of artifacts to format

    Returns:
        Formatted verbose list with full metadata per artifact
    """
    if not artifacts:
        return ""

    lines = []
    sorted_artifacts = sorted(artifacts, key=lambda a: (a.artifact_type, a.artifact_name))
    for i, artifact in enumerate(sorted_artifacts):
        if i > 0:
            lines.append("")  # Blank line between artifacts

        lines.append(format_artifact_header(artifact))

        # Add hook-specific metadata
        if artifact.artifact_type == "hook":
            hook_meta = format_hook_metadata(artifact)
            if hook_meta:
                lines.append(hook_meta)

    return "\n".join(lines)
