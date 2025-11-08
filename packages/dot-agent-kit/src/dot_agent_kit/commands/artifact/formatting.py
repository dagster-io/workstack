"""Formatting functions for artifact display output."""

from pathlib import Path

import click

from dot_agent_kit.models.artifact import ArtifactLevel, ArtifactSource, InstalledArtifact
from dot_agent_kit.models.bundled_kit import BundledKitInfo


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


def format_artifact_header(artifact: InstalledArtifact, absolute_path: Path | None = None) -> str:
    """Format metadata header for artifact show command.

    Args:
        artifact: Artifact to format header for
        absolute_path: Optional absolute filesystem path to display

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

    # Display absolute path if provided, otherwise use relative path
    # When absolute path is provided, only display that (not both paths)
    if absolute_path:
        lines.append(f"Path: {absolute_path}")
    else:
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


def format_bundled_kit_item(item_name: str, kit_info: BundledKitInfo, item_type: str) -> str:
    """Format single-line representation of a bundled kit item.

    Args:
        item_name: Name of the item (command name or doc path)
        kit_info: Kit information containing version and level
        item_type: Type of item ("cli_command" or "doc")

    Returns:
        Formatted line: [level] name [kit@version]
    """
    level_indicator = (
        click.style("[U]", fg="blue", bold=True)
        if kit_info.level == "user"
        else click.style("[P]", fg="green", bold=True)
    )

    # Format name based on item type
    if item_type == "cli_command":
        display_name = f"{kit_info.kit_id}:{item_name}"
    else:  # doc
        display_name = item_name

    name = click.style(display_name, bold=True)
    source = click.style(f"[{kit_info.kit_id}@{kit_info.version}]", fg="cyan")

    return f"{level_indicator} {name} {source}"


def format_compact_list(
    artifacts: list[InstalledArtifact], bundled_kits: dict[str, BundledKitInfo] | None = None
) -> str:
    """Format compact view grouped by type with two sections.

    Creates output structure:
    - Claude Artifacts: skills, commands, agents, hooks
    - Installed Items: docs, kit CLI commands

    Args:
        artifacts: List of artifacts to format
        bundled_kits: Dict of bundled kit information

    Returns:
        Formatted compact list with two-section structure
    """
    if bundled_kits is None:
        bundled_kits = {}

    if not artifacts and not bundled_kits:
        return ""

    # Group artifacts by type
    by_type: dict[str, list[InstalledArtifact]] = {}
    for artifact in artifacts:
        if artifact.artifact_type not in by_type:
            by_type[artifact.artifact_type] = []
        by_type[artifact.artifact_type].append(artifact)

    lines = []

    # Section 1: Claude Artifacts (skills, commands, agents, hooks)
    claude_artifact_types = ["skill", "command", "agent", "hook"]
    has_claude_artifacts = any(t in by_type for t in claude_artifact_types)

    if has_claude_artifacts:
        lines.append(click.style("Claude Artifacts:", bold=True, fg="white"))

        for artifact_type in claude_artifact_types:
            if artifact_type not in by_type:
                continue

            type_artifacts = by_type[artifact_type]
            lines.append(click.style(f"  {artifact_type.capitalize()}s:", bold=True, fg="white"))

            for artifact in sorted(type_artifacts, key=lambda a: a.artifact_name):
                lines.append(f"    {format_compact_artifact_line(artifact)}")

    # Section 2: Installed Items (docs, kit CLI commands)
    has_docs = "doc" in by_type
    has_kit_commands = any(kit.cli_commands for kit in bundled_kits.values())

    if has_docs or has_kit_commands:
        if has_claude_artifacts:
            lines.append("")  # Blank line between sections

        lines.append(click.style("Installed Items:", bold=True, fg="white"))

        # Docs subsection
        if has_docs:
            lines.append(click.style("  Docs:", bold=True, fg="white"))
            for artifact in sorted(by_type["doc"], key=lambda a: a.artifact_name):
                lines.append(f"    {format_compact_artifact_line(artifact)}")

        # Kit CLI Commands subsection
        if has_kit_commands:
            lines.append(click.style("  Kit CLI Commands:", bold=True, fg="white"))

            # Collect all commands from all kits
            all_commands: list[tuple[str, BundledKitInfo]] = []
            for kit_info in bundled_kits.values():
                for cmd_name in kit_info.cli_commands:
                    all_commands.append((cmd_name, kit_info))

            # Sort by full command name (kit:command)
            all_commands.sort(key=lambda x: f"{x[1].kit_id}:{x[0]}")

            for cmd_name, kit_info in all_commands:
                lines.append(f"    {format_bundled_kit_item(cmd_name, kit_info, 'cli_command')}")

    return "\n".join(lines)


def format_verbose_list(
    artifacts: list[InstalledArtifact], bundled_kits: dict[str, BundledKitInfo] | None = None
) -> str:
    """Format detailed view with metadata in two sections.

    Creates output structure:
    - Claude Artifacts: skills, commands, agents, hooks with full metadata
    - Installed Items: docs and kit CLI commands with full metadata

    Args:
        artifacts: List of artifacts to format
        bundled_kits: Dict of bundled kit information

    Returns:
        Formatted verbose list with full metadata per item
    """
    if bundled_kits is None:
        bundled_kits = {}

    if not artifacts and not bundled_kits:
        return ""

    # Group artifacts by type
    by_type: dict[str, list[InstalledArtifact]] = {}
    for artifact in artifacts:
        if artifact.artifact_type not in by_type:
            by_type[artifact.artifact_type] = []
        by_type[artifact.artifact_type].append(artifact)

    lines = []

    # Section 1: Claude Artifacts
    claude_artifact_types = ["skill", "command", "agent", "hook"]
    has_claude_artifacts = any(t in by_type for t in claude_artifact_types)

    if has_claude_artifacts:
        lines.append(click.style("Claude Artifacts:", bold=True, fg="white"))
        lines.append("")

        first_artifact = True
        for artifact_type in claude_artifact_types:
            if artifact_type not in by_type:
                continue

            type_artifacts = sorted(by_type[artifact_type], key=lambda a: a.artifact_name)
            for artifact in type_artifacts:
                if not first_artifact:
                    lines.append("")

                lines.append(format_artifact_header(artifact))

                if artifact.artifact_type == "hook":
                    hook_meta = format_hook_metadata(artifact)
                    if hook_meta:
                        lines.append(hook_meta)

                first_artifact = False

    # Section 2: Installed Items
    has_docs = "doc" in by_type
    has_kit_commands = any(kit.cli_commands for kit in bundled_kits.values())

    if has_docs or has_kit_commands:
        if has_claude_artifacts:
            lines.append("")
            lines.append("")

        lines.append(click.style("Installed Items:", bold=True, fg="white"))
        lines.append("")

        first_item = True

        # Docs
        if has_docs:
            for artifact in sorted(by_type["doc"], key=lambda a: a.artifact_name):
                if not first_item:
                    lines.append("")

                lines.append(format_artifact_header(artifact))
                first_item = False

        # Kit CLI Commands
        if has_kit_commands:
            all_commands: list[tuple[str, BundledKitInfo]] = []
            for kit_info in bundled_kits.values():
                for cmd_name in kit_info.cli_commands:
                    all_commands.append((cmd_name, kit_info))

            all_commands.sort(key=lambda x: f"{x[1].kit_id}:{x[0]}")

            for cmd_name, kit_info in all_commands:
                if not first_item:
                    lines.append("")

                # Format metadata for kit CLI command
                full_name = f"{kit_info.kit_id}:{cmd_name}"
                lines.append(click.style(f"Artifact: {full_name}", bold=True, fg="white"))
                lines.append("Type: kit_cli_command")
                lines.append(f"Level: {kit_info.level}")
                lines.append(f"Kit: {kit_info.kit_id}")
                lines.append(f"Version: {kit_info.version}")

                first_item = False

    return "\n".join(lines)
