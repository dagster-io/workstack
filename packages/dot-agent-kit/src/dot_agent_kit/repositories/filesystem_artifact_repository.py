"""Filesystem-based artifact repository implementation."""

from pathlib import Path

from dot_agent_kit.models.artifact import ArtifactSource, InstalledArtifact
from dot_agent_kit.models.config import InstalledKit, ProjectConfig
from dot_agent_kit.repositories.artifact_repository import ArtifactRepository


class FilesystemArtifactRepository(ArtifactRepository):
    """Discovers artifacts from filesystem .claude/ directory."""

    def discover_all_artifacts(
        self, project_dir: Path, config: ProjectConfig
    ) -> list[InstalledArtifact]:
        """Discover all installed artifacts with their metadata.

        Scans the .claude/ directory for all artifacts and enriches them with
        source information (managed or local).

        Args:
            project_dir: Project root directory
            config: Project configuration from dot-agent.toml

        Returns:
            List of all installed artifacts with metadata
        """
        claude_dir = project_dir / ".claude"
        if not claude_dir.exists():
            return []

        artifacts: list[InstalledArtifact] = []

        # Map of artifact paths to installed kits for tracking managed status
        managed_artifacts: dict[str, InstalledKit] = {}
        for kit in config.kits.values():
            for artifact_path in kit.artifacts:
                managed_artifacts[artifact_path] = kit

        # Scan skills directory
        skills_dir = claude_dir / "skills"
        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if not skill_dir.is_dir():
                    continue

                skill_file = skill_dir / "SKILL.md"
                if not skill_file.exists():
                    continue

                artifact = self._create_artifact_from_file(
                    skill_file, "skill", skill_dir.name, managed_artifacts, config
                )
                if artifact:
                    artifacts.append(artifact)

        # Scan commands directory
        commands_dir = claude_dir / "commands"
        if commands_dir.exists():
            for item in commands_dir.iterdir():
                if item.is_file() and item.suffix == ".md":
                    # Direct command file: commands/command-name.md
                    name = item.stem
                    artifact = self._create_artifact_from_file(
                        item, "command", name, managed_artifacts, config
                    )
                    if artifact:
                        artifacts.append(artifact)
                elif item.is_dir():
                    # Kit commands directory: commands/kit-name/*.md
                    for cmd_file in item.glob("*.md"):
                        # Format as "kit:command-name"
                        name = f"{item.name}:{cmd_file.stem}"
                        artifact = self._create_artifact_from_file(
                            cmd_file, "command", name, managed_artifacts, config
                        )
                        if artifact:
                            artifacts.append(artifact)

        # Scan agents directory
        agents_dir = claude_dir / "agents"
        if agents_dir.exists():
            for item in agents_dir.iterdir():
                if item.is_file() and item.suffix == ".md":
                    # Direct agent file: agents/agent-name.md
                    name = item.stem
                    artifact = self._create_artifact_from_file(
                        item, "agent", name, managed_artifacts, config
                    )
                    if artifact:
                        artifacts.append(artifact)
                elif item.is_dir():
                    # Kit agents directory: agents/kit-name/*.md
                    for agent_file in item.glob("*.md"):
                        name = agent_file.stem
                        artifact = self._create_artifact_from_file(
                            agent_file, "agent", name, managed_artifacts, config
                        )
                        if artifact:
                            artifacts.append(artifact)

        return artifacts

    def _create_artifact_from_file(
        self,
        file_path: Path,
        artifact_type: str,
        display_name: str,
        managed_artifacts: dict[str, InstalledKit],
        config: ProjectConfig,
    ) -> InstalledArtifact | None:
        """Create an InstalledArtifact from a file.

        Args:
            file_path: Path to the artifact file
            artifact_type: Type of artifact (skill, command, agent)
            display_name: Display name for the artifact
            managed_artifacts: Map of artifact paths to installed kits
            config: Project configuration

        Returns:
            InstalledArtifact or None if file doesn't exist
        """
        if not file_path.exists():
            return None

        # Get relative path from .claude/ directory
        claude_dir = file_path.parent
        while claude_dir.name != ".claude" and claude_dir.parent != claude_dir:
            claude_dir = claude_dir.parent
        relative_path = file_path.relative_to(claude_dir)

        # Determine source and kit info
        source = ArtifactSource.LOCAL
        kit_id = None
        kit_version = None

        # Check if it's a managed artifact
        # Config paths may include ".claude/" prefix, so check both variations
        for artifact_path, kit in managed_artifacts.items():
            normalized_artifact = artifact_path.replace(".claude/", "").replace("\\", "/")
            normalized_relative = str(relative_path).replace("\\", "/")

            if normalized_relative == normalized_artifact:
                source = ArtifactSource.MANAGED
                kit_id = kit.kit_id
                kit_version = kit.version
                break

        # If not managed, it's a local artifact

        return InstalledArtifact(
            artifact_type=artifact_type,
            artifact_name=display_name,
            file_path=relative_path,
            source=source,
            kit_id=kit_id,
            kit_version=kit_version,
        )
