"""Project directory installation operations."""

from pathlib import Path

from dot_agent_kit.models import (
    ConflictPolicy,
    InstallationContext,
    InstalledKit,
)
from dot_agent_kit.operations.install import install_kit as install_kit_base
from dot_agent_kit.sources import ResolvedKit


def install_kit_to_project(
    resolved: ResolvedKit,
    context: InstallationContext,
    conflict_policy: ConflictPolicy = ConflictPolicy.ERROR,
    filtered_artifacts: dict[str, list[str]] | None = None,
) -> InstalledKit:
    """Install a kit to project directory.

    Args:
        resolved: Resolved kit to install
        context: Installation context
        conflict_policy: How to handle file conflicts
        filtered_artifacts: Optional filtered artifacts (from ArtifactSpec.filter_artifacts())

    Returns:
        InstalledKit with installation metadata
    """
    return install_kit_base(resolved, context.base_path, conflict_policy, filtered_artifacts)


def get_installation_context(project_dir: Path | None = None) -> InstallationContext:
    """Create installation context for the project.

    Args:
        project_dir: Project directory (defaults to current working directory)

    Returns:
        InstallationContext configured for the project
    """
    if project_dir is None:
        project_dir = Path.cwd()
    return InstallationContext(project_dir)
