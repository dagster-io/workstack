"""List command for showing installed artifacts."""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import click
import pathspec

from dot_agent_kit.io import (
    create_default_config,
    load_project_config,
)
from dot_agent_kit.models.artifact import ArtifactSource, InstalledArtifact
from dot_agent_kit.models.config import ProjectConfig
from dot_agent_kit.repositories import ArtifactRepository, FilesystemArtifactRepository


@dataclass(frozen=True)
class ArtifactDisplayData:
    """Captures display information for an artifact to avoid recalculating."""

    artifact: InstalledArtifact
    folder_path: str
    file_counts: str
    source: str


def _format_source(artifact: InstalledArtifact) -> str:
    """Format the source attribution string for an artifact.

    Args:
        artifact: The artifact to format

    Returns:
        Formatted source string like "[devrun@0.1.0]" or "[local]"
    """
    if artifact.source == ArtifactSource.LOCAL:
        return "[local]"
    elif artifact.kit_id and artifact.kit_version:
        return f"[{artifact.kit_id}@{artifact.kit_version}]"
    elif artifact.kit_id:
        return f"[{artifact.kit_id}]"
    else:
        return "[unknown]"


def _find_project_root(start_path: Path) -> Path:
    """Find the project root by searching for .git directory.

    Args:
        start_path: Directory to start searching from

    Returns:
        Project root directory (directory containing .git) or start_path if not found
    """
    current = start_path.resolve() if start_path.exists() else start_path
    home = Path.home()

    while current != current.parent and current != home:
        git_dir = current / ".git"
        if git_dir.exists():
            return current
        current = current.parent

    return start_path


def _count_files_by_extension(artifact_dir: Path, project_root: Path) -> str:
    """Count files in artifact directory grouped by extension, respecting .gitignore.

    Args:
        artifact_dir: Directory containing the artifact files
        project_root: Project root directory for gitignore resolution

    Returns:
        Formatted string like "5 .md, 3 .py, 2 .json, 3 others"
    """
    # Check if artifact directory exists
    if not artifact_dir.exists():
        return ""

    # Read .gitignore from project root if it exists
    gitignore_path = project_root / ".gitignore"
    spec: pathspec.PathSpec | None = None

    if gitignore_path.exists():
        gitignore_content = gitignore_path.read_text(encoding="utf-8")
        spec = pathspec.PathSpec.from_lines("gitwildmatch", gitignore_content.splitlines())

    # Count files by extension
    extension_counts: Counter[str] = Counter()

    for file_path in artifact_dir.rglob("*"):
        # Skip directories
        if not file_path.is_file():
            continue

        # Get relative path from project root for gitignore matching
        if file_path.exists() and project_root.exists():
            relative_path = file_path.resolve().relative_to(project_root.resolve())

            # Check if file matches gitignore patterns
            if spec is not None and spec.match_file(str(relative_path)):
                continue

        # Count by extension
        extension = file_path.suffix if file_path.suffix else ""
        extension_counts[extension] += 1

    # Format output: top 3 extensions + others
    if not extension_counts:
        return ""

    # Sort by count descending to find the most common extensions
    sorted_by_count = sorted(extension_counts.items(), key=lambda item: -item[1])

    # Take top 3 most common extensions
    top_3_by_count = sorted_by_count[:3]
    remaining = sorted_by_count[3:]

    # Sort the top 3 alphabetically by extension name for consistent display
    top_3_sorted = sorted(top_3_by_count, key=lambda item: item[0])

    # Format top 3
    parts = [
        f"{ext.lstrip('.')} ({count})" if ext else f"no-ext ({count})"
        for ext, count in top_3_sorted
    ]

    # Add remaining count if any
    if remaining:
        remaining_count = sum(count for _, count in remaining)
        parts.append(f"others ({remaining_count})")

    return ", ".join(parts)


def _list_artifacts(
    config: ProjectConfig,
    project_dir: Path,
    repository: ArtifactRepository,
) -> None:
    """List all installed artifacts in artifact-focused format.

    Args:
        config: Project configuration
        project_dir: Project directory for artifact discovery
        repository: Repository for artifact discovery
    """
    # Discover all artifacts using the provided repository
    artifacts = repository.discover_all_artifacts(project_dir, config)

    if not artifacts:
        click.echo("No artifacts installed")
        return

    # Find project root for gitignore resolution
    project_root = _find_project_root(project_dir)

    # Group artifacts by type
    skills: list[InstalledArtifact] = []
    commands: list[InstalledArtifact] = []
    agents: list[InstalledArtifact] = []
    hooks: list[InstalledArtifact] = []

    for artifact in artifacts:
        if artifact.artifact_type == "skill":
            skills.append(artifact)
        elif artifact.artifact_type == "command":
            commands.append(artifact)
        elif artifact.artifact_type == "agent":
            agents.append(artifact)
        elif artifact.artifact_type == "hook":
            hooks.append(artifact)

    # Create display data only for skills
    skills_data: list[ArtifactDisplayData] = []
    for skill in skills:
        folder_path = str(skill.file_path.parent) + "/"
        # Artifact file_path is relative to .claude/, so prepend .claude/
        artifact_dir = project_dir / ".claude" / skill.file_path.parent
        file_counts = _count_files_by_extension(artifact_dir, project_root)
        source = _format_source(skill)

        display_data = ArtifactDisplayData(
            artifact=skill,
            folder_path=folder_path,
            file_counts=file_counts,
            source=source,
        )
        skills_data.append(display_data)

    # Calculate column widths for alignment
    max_name_len = 0
    max_path_len = 0  # For commands and agents (file path)
    max_folder_len = 0  # For skills (folder path)
    max_counts_len = 0  # For skills (file counts)

    # Calculate max name length across all artifacts
    for artifact in artifacts:
        max_name_len = max(max_name_len, len(artifact.artifact_name))

    # Calculate widths for skills
    for data in skills_data:
        max_folder_len = max(max_folder_len, len(data.folder_path))
        max_counts_len = max(max_counts_len, len(data.file_counts))

    # Calculate widths for commands, agents, and hooks (file paths)
    for artifact in commands + agents + hooks:
        max_path_len = max(max_path_len, len(str(artifact.file_path)))

    # Ensure minimum widths
    max_name_len = max(max_name_len, 20)
    max_path_len = max(max_path_len, 30)
    max_folder_len = max(max_folder_len, 30)
    max_counts_len = max(max_counts_len, 20)

    # Display skills
    if skills_data:
        click.echo("Skills:")
        for data in sorted(skills_data, key=lambda d: d.artifact.artifact_name):
            name = data.artifact.artifact_name.ljust(max_name_len)
            folder_path = data.folder_path.ljust(max_folder_len)
            file_counts = data.file_counts.ljust(max_counts_len)
            click.echo(f"  {name} {folder_path} {file_counts} {data.source}")
        click.echo()

    # Display commands
    if commands:
        click.echo("Commands:")
        for command in sorted(commands, key=lambda a: a.artifact_name):
            name = command.artifact_name.ljust(max_name_len)
            source = _format_source(command)
            file_path = str(command.file_path).ljust(max_path_len)
            click.echo(f"  {name} {source.ljust(20)} {file_path}")
        click.echo()

    # Display agents
    if agents:
        click.echo("Agents:")
        for agent in sorted(agents, key=lambda a: a.artifact_name):
            name = agent.artifact_name.ljust(max_name_len)
            source = _format_source(agent)
            file_path = str(agent.file_path).ljust(max_path_len)
            click.echo(f"  {name} {source.ljust(20)} {file_path}")
        click.echo()

    # Display hooks
    if hooks:
        click.echo("Hooks:")
        for hook in sorted(hooks, key=lambda a: a.artifact_name):
            name = hook.artifact_name.ljust(max_name_len)
            source = _format_source(hook)
            file_path = str(hook.file_path).ljust(max_path_len)
            click.echo(f"  {name} {source.ljust(20)} {file_path}")


@click.command("list")
def list_cmd() -> None:
    """List all installed artifacts."""
    # Load project config
    project_dir = Path.cwd()
    loaded_config = load_project_config(project_dir)
    config = loaded_config if loaded_config is not None else create_default_config()

    # Create filesystem repository for production use
    repository = FilesystemArtifactRepository()
    _list_artifacts(config, project_dir, repository)


@click.command("ls", hidden=True)
def ls_cmd() -> None:
    """List all installed artifacts."""
    # Load project config
    project_dir = Path.cwd()
    loaded_config = load_project_config(project_dir)
    config = loaded_config if loaded_config is not None else create_default_config()

    # Create filesystem repository for production use
    repository = FilesystemArtifactRepository()
    _list_artifacts(config, project_dir, repository)
