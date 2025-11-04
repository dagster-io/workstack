"""Filesystem-based artifact repository implementation."""

from pathlib import Path

from dot_agent_kit.hooks.settings import extract_kit_id_from_command, get_all_hooks, load_settings
from dot_agent_kit.models.artifact import ArtifactLevel, ArtifactSource, ArtifactType, InstalledArtifact
from dot_agent_kit.models.config import InstalledKit, ProjectConfig
from dot_agent_kit.repositories.artifact_repository import ArtifactRepository


class FilesystemArtifactRepository(ArtifactRepository):
    """Discovers artifacts from filesystem .claude/ directory."""

    def __init__(self, level: ArtifactLevel | None = None) -> None:
        """Initialize repository with optional artifact level.

        Args:
            level: The artifact level (USER or PROJECT). If None, defaults to PROJECT.
        """
        self._level = level if level is not None else ArtifactLevel.PROJECT

    @classmethod
    def for_user(cls) -> "FilesystemArtifactRepository":
        """Create a repository for user-level artifacts (~/.claude/)."""
        return cls(level=ArtifactLevel.USER)

    @classmethod
    def for_project(cls) -> "FilesystemArtifactRepository":
        """Create a repository for project-level artifacts (./.claude/)."""
        return cls(level=ArtifactLevel.PROJECT)

    def discover_all_artifacts(
        self, project_dir: Path, config: ProjectConfig
    ) -> list[InstalledArtifact]:
        """Discover all installed artifacts with their metadata.

        Scans the .claude/ directory for all artifacts and enriches them with
        source information (managed, unmanaged, or local).

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
                    skill_file, "skill", skill_dir.name, managed_artifacts, config, self._level
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
                        item, "command", name, managed_artifacts, config, self._level
                    )
                    if artifact:
                        artifacts.append(artifact)
                elif item.is_dir():
                    # Kit commands directory: commands/kit-name/*.md
                    for cmd_file in item.glob("*.md"):
                        # Format as "kit:command-name"
                        name = f"{item.name}:{cmd_file.stem}"
                        artifact = self._create_artifact_from_file(
                            cmd_file, "command", name, managed_artifacts, config, self._level
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
                        item, "agent", name, managed_artifacts, config, self._level
                    )
                    if artifact:
                        artifacts.append(artifact)
                elif item.is_dir():
                    # Kit agents directory: agents/kit-name/*.md
                    for agent_file in item.glob("*.md"):
                        name = agent_file.stem
                        artifact = self._create_artifact_from_file(
                            agent_file, "agent", name, managed_artifacts, config, self._level
                        )
                        if artifact:
                            artifacts.append(artifact)

        # Discover hooks from settings files and filesystem
        hook_artifacts = self._discover_hooks(claude_dir, managed_artifacts)
        artifacts.extend(hook_artifacts)

        return artifacts

    def _create_artifact_from_file(
        self,
        file_path: Path,
        artifact_type: ArtifactType,
        display_name: str,
        managed_artifacts: dict[str, InstalledKit],
        config: ProjectConfig,
        level: ArtifactLevel,
    ) -> InstalledArtifact | None:
        """Create an InstalledArtifact from a file.

        Args:
            file_path: Path to the artifact file
            artifact_type: Type of artifact (skill, command, agent)
            display_name: Display name for the artifact
            managed_artifacts: Map of artifact paths to installed kits
            config: Project configuration
            level: The artifact level (USER or PROJECT)

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
            level=level,
        )

    def _discover_hooks(
        self, claude_dir: Path, managed_artifacts: dict[str, InstalledKit]
    ) -> list[InstalledArtifact]:
        """Discover hooks from settings files and filesystem.

        Args:
            claude_dir: Path to .claude directory
            managed_artifacts: Map of artifact paths to installed kits

        Returns:
            List of hook artifacts from all sources
        """
        # Parse hooks from both settings files
        settings_hooks = self._parse_settings_hooks(claude_dir, "settings.json", managed_artifacts)
        local_settings_hooks = self._parse_settings_hooks(
            claude_dir, "settings.local.json", managed_artifacts
        )

        # Scan filesystem for orphaned hooks
        orphaned_hooks = self._scan_orphaned_hooks(
            claude_dir, settings_hooks + local_settings_hooks
        )

        # Combine all hooks
        return settings_hooks + local_settings_hooks + orphaned_hooks

    def _parse_settings_hooks(
        self,
        claude_dir: Path,
        settings_filename: str,
        managed_artifacts: dict[str, InstalledKit],
    ) -> list[InstalledArtifact]:
        """Parse hooks from a specific settings file.

        Args:
            claude_dir: Path to .claude directory
            settings_filename: Name of settings file (e.g., "settings.json")
            managed_artifacts: Map of artifact paths to installed kits

        Returns:
            List of hook artifacts from this settings file
        """
        settings_path = claude_dir / settings_filename
        if not settings_path.exists():
            return []

        settings = load_settings(settings_path)
        hooks = get_all_hooks(settings)

        artifacts: list[InstalledArtifact] = []

        for lifecycle, matcher, entry in hooks:
            # Extract script path from command
            command = entry.command
            script_path = self._extract_script_path(command)

            # Extract hook metadata
            hook_name, kit_id, source, kit_version = self._extract_hook_metadata(
                entry, script_path, managed_artifacts
            )

            # Create artifact with enhanced metadata
            artifact = InstalledArtifact(
                artifact_type="hook",
                artifact_name=hook_name,
                file_path=script_path,
                source=source,
                kit_id=kit_id,
                kit_version=kit_version,
                level=self._level,
                settings_source=settings_filename,
                lifecycle=lifecycle,
                matcher=matcher,
                timeout=entry.timeout,
            )
            artifacts.append(artifact)

        return artifacts

    def _extract_script_path(self, command: str) -> Path:
        """Extract script path from hook command.

        Args:
            command: Hook command string

        Returns:
            Path object representing the script path relative to .claude/
        """
        if ".claude/hooks/" in command:
            parts = command.split(".claude/")
            if len(parts) > 1:
                path_part = parts[1].split()[0]  # Take first token
                return Path(path_part)

        # Fallback for commands without recognizable path
        return Path("hooks") / "unknown-hook"

    def _extract_hook_metadata(
        self,
        entry,
        script_path: Path,
        managed_artifacts: dict[str, InstalledKit],
    ) -> tuple[str, str | None, ArtifactSource, str | None]:
        """Extract hook metadata from hook entry.

        Args:
            entry: HookEntry from settings
            script_path: Path to hook script
            managed_artifacts: Map of artifact paths to installed kits

        Returns:
            Tuple of (hook_name, kit_id, source, kit_version)
        """
        import re

        entry_kit_id = extract_kit_id_from_command(entry.command)

        if entry_kit_id:
            # Hook with kit metadata
            hook_id_match = re.search(r"DOT_AGENT_HOOK_ID=(\S+)", entry.command)
            entry_hook_id = hook_id_match.group(1) if hook_id_match else "unknown"
            hook_name = f"{entry_kit_id}:{entry_hook_id}"
            kit_id = entry_kit_id
            source = ArtifactSource.LOCAL
            kit_version = None

            # Check if this hook is managed
            hook_path_str = str(script_path).replace("\\", "/")
            for artifact_path, kit in managed_artifacts.items():
                normalized_artifact = artifact_path.replace(".claude/", "").replace("\\", "/")
                matches_path = normalized_artifact == hook_path_str
                matches_kit = kit.kit_id == entry_kit_id
                if matches_path or matches_kit:
                    source = ArtifactSource.MANAGED
                    kit_version = kit.version
                    break

            return hook_name, kit_id, source, kit_version

        # Local hook without kit metadata
        hook_name = script_path.stem if script_path.stem != "unknown-hook" else entry.command[:50]
        return hook_name, None, ArtifactSource.LOCAL, None

    def _scan_orphaned_hooks(
        self, claude_dir: Path, referenced_hooks: list[InstalledArtifact]
    ) -> list[InstalledArtifact]:
        """Scan filesystem for hooks not referenced in any settings file.

        Args:
            claude_dir: Path to .claude directory
            referenced_hooks: List of hooks found in settings files

        Returns:
            List of orphaned hook artifacts
        """
        hooks_dir = claude_dir / "hooks"
        if not hooks_dir.exists():
            return []

        # Collect all script paths referenced in settings
        referenced_paths = {str(hook.file_path) for hook in referenced_hooks}

        orphaned: list[InstalledArtifact] = []

        # Scan all .py files in hooks directory
        for script_file in hooks_dir.rglob("*.py"):
            if not script_file.is_file():
                continue

            # Get relative path from claude_dir
            relative_path = script_file.relative_to(claude_dir)
            path_str = str(relative_path).replace("\\", "/")

            # Check if this script is referenced in settings
            if path_str not in referenced_paths:
                # This is an orphaned hook
                hook_name = f"{script_file.parent.name}:{script_file.stem}"
                artifact = InstalledArtifact(
                    artifact_type="hook",
                    artifact_name=hook_name,
                    file_path=relative_path,
                    source=ArtifactSource.LOCAL,
                    kit_id=None,
                    kit_version=None,
                    level=self._level,
                    settings_source="orphaned",
                )
                orphaned.append(artifact)

        return orphaned
