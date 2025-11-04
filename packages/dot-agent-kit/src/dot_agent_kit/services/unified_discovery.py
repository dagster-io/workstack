"""Unified artifact discovery across user and project levels."""

from dataclasses import dataclass
from pathlib import Path

from dot_agent_kit.io import create_default_config, load_project_config
from dot_agent_kit.models.artifact import ArtifactLevel, ArtifactSource, InstalledArtifact
from dot_agent_kit.repositories.filesystem_artifact_repository import FilesystemArtifactRepository


@dataclass(frozen=True)
class UnifiedDiscoveryResult:
    """Result of unified artifact discovery across levels."""

    user_artifacts: list[InstalledArtifact]
    project_artifacts: list[InstalledArtifact]

    def all_artifacts(self) -> list[InstalledArtifact]:
        """Return all artifacts from both levels combined.

        Returns:
            Combined list of user and project artifacts
        """
        return self.user_artifacts + self.project_artifacts

    def filter_by_type(self, artifact_type: str) -> "UnifiedDiscoveryResult":
        """Filter artifacts by type.

        Args:
            artifact_type: Type to filter by (skill, command, agent, hook)

        Returns:
            New UnifiedDiscoveryResult with filtered artifacts
        """
        filtered_user = [a for a in self.user_artifacts if a.artifact_type == artifact_type]
        filtered_project = [a for a in self.project_artifacts if a.artifact_type == artifact_type]
        return UnifiedDiscoveryResult(
            user_artifacts=filtered_user,
            project_artifacts=filtered_project,
        )

    def filter_by_level(self, level: ArtifactLevel) -> list[InstalledArtifact]:
        """Filter artifacts by level.

        Args:
            level: Level to filter by (USER or PROJECT)

        Returns:
            List of artifacts at the specified level
        """
        if level == ArtifactLevel.USER:
            return self.user_artifacts
        return self.project_artifacts

    def filter_by_source(self, source: ArtifactSource) -> "UnifiedDiscoveryResult":
        """Filter artifacts by source.

        Args:
            source: Source to filter by (MANAGED or LOCAL)

        Returns:
            New UnifiedDiscoveryResult with filtered artifacts
        """
        filtered_user = [a for a in self.user_artifacts if a.source == source]
        filtered_project = [a for a in self.project_artifacts if a.source == source]
        return UnifiedDiscoveryResult(
            user_artifacts=filtered_user,
            project_artifacts=filtered_project,
        )


class UnifiedArtifactDiscovery:
    """Discovers artifacts across user and project levels."""

    def discover_all(
        self, project_dir: Path | None = None, user_home: Path | None = None
    ) -> UnifiedDiscoveryResult:
        """Discover all artifacts from both user and project levels.

        Args:
            project_dir: Optional project directory. If None, uses current directory.
            user_home: Optional user home directory. If None, uses Path.home().

        Returns:
            UnifiedDiscoveryResult with artifacts from both levels
        """
        # Determine directories
        if project_dir is None:
            project_dir = Path.cwd()
        if user_home is None:
            user_home = Path.home()

        # Load configurations
        # load_project_config looks for dot-agent.toml in the given directory
        project_config = load_project_config(project_dir / ".claude")
        if not project_config:
            project_config = create_default_config()

        user_config = load_project_config(user_home / ".claude")
        if not user_config:
            user_config = create_default_config()

        # Discover from both levels
        user_repo = FilesystemArtifactRepository.for_user()
        project_repo = FilesystemArtifactRepository.for_project()

        user_artifacts = user_repo.discover_all_artifacts(user_home, user_config)
        project_artifacts = project_repo.discover_all_artifacts(project_dir, project_config)

        return UnifiedDiscoveryResult(
            user_artifacts=user_artifacts,
            project_artifacts=project_artifacts,
        )

    def discover_with_filters(
        self,
        artifact_type: str | None = None,
        level: ArtifactLevel | None = None,
        source: ArtifactSource | None = None,
        project_dir: Path | None = None,
        user_home: Path | None = None,
    ) -> list[InstalledArtifact]:
        """Discover artifacts with optional filters applied.

        Args:
            artifact_type: Optional type filter (skill, command, agent, hook)
            level: Optional level filter (USER or PROJECT)
            source: Optional source filter (MANAGED or LOCAL)
            project_dir: Optional project directory
            user_home: Optional user home directory

        Returns:
            List of artifacts matching all specified filters
        """
        # Discover all
        result = self.discover_all(project_dir, user_home)

        # Apply type filter
        if artifact_type is not None:
            result = result.filter_by_type(artifact_type)

        # Apply source filter
        if source is not None:
            result = result.filter_by_source(source)

        # Apply level filter and return as flat list
        if level is not None:
            return result.filter_by_level(level)

        return result.all_artifacts()
