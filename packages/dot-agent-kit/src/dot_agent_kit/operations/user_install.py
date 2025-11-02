"""User directory installation operations."""

from pathlib import Path

from dot_agent_kit.io import get_user_claude_dir
from dot_agent_kit.models import (
    ConflictPolicy,
    InstallationContext,
    InstallationTarget,
    InstalledKit,
)
from dot_agent_kit.operations.install import install_kit as install_kit_base
from dot_agent_kit.sources import ResolvedKit


def install_kit_to_target(
    resolved: ResolvedKit,
    context: InstallationContext,
    conflict_policy: ConflictPolicy = "error",
    filtered_artifacts: dict[str, list[str]] | None = None,
) -> InstalledKit:
    """Install a kit to either user or project directory.

    Args:
        resolved: Resolved kit to install
        context: Installation context (user or project)
        conflict_policy: How to handle file conflicts
        filtered_artifacts: Optional filtered artifacts (from ArtifactSpec.filter_artifacts())

    Returns:
        InstalledKit with installation metadata
    """
    if context.target == "user":
        # Install to user directory (~/.claude)
        user_dir = get_user_claude_dir()
        return install_kit_base(resolved, user_dir, conflict_policy, filtered_artifacts)
    else:
        # Install to project directory
        return install_kit_base(resolved, context.base_path, conflict_policy, filtered_artifacts)


def get_installation_context(
    target: InstallationTarget,
    project_dir: Path | None = None,
) -> InstallationContext:
    """Create installation context for the given target.

    Args:
        target: Where to install (user or project)
        project_dir: Project directory (required for project installs, ignored for user)

    Returns:
        InstallationContext configured for the target
    """
    if target == "user":
        return InstallationContext(target, Path.home())
    else:
        if project_dir is None:
            project_dir = Path.cwd()
        return InstallationContext(target, project_dir)
