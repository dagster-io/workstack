"""Kit installation operations."""

from datetime import datetime
from pathlib import Path

import click

from dot_agent_kit.io import load_kit_manifest
from dot_agent_kit.models import ConflictPolicy, InstalledKit
from dot_agent_kit.sources import ResolvedKit


def install_kit(
    resolved: ResolvedKit,
    project_dir: Path,
    conflict_policy: ConflictPolicy = ConflictPolicy.ERROR,
    filtered_artifacts: dict[str, list[str]] | None = None,
) -> InstalledKit:
    """Install a kit to the project.

    Args:
        resolved: Resolved kit to install
        project_dir: Directory to install to
        conflict_policy: How to handle file conflicts
        filtered_artifacts: Optional filtered artifacts dict (type -> paths).
                          If None, installs all artifacts from manifest.
    """
    manifest = load_kit_manifest(resolved.manifest_path)
    claude_dir = project_dir / ".claude"

    # Create .claude directory if needed
    if not claude_dir.exists():
        claude_dir.mkdir(parents=True)

    installed_artifacts: list[str] = []

    # Use filtered artifacts if provided, otherwise use all from manifest
    artifacts_to_install = (
        filtered_artifacts if filtered_artifacts is not None else manifest.artifacts
    )

    # Process each artifact type
    for artifact_type, paths in artifacts_to_install.items():
        # Map artifact type to .claude subdirectory
        target_dir = claude_dir / f"{artifact_type}s"  # agents, commands, skills
        if not target_dir.exists():
            target_dir.mkdir(parents=True)

        for artifact_path in paths:
            # Read source artifact
            source = resolved.artifacts_base / artifact_path
            if not source.exists():
                continue

            content = source.read_text(encoding="utf-8")

            # Determine target path - preserve nested directory structure
            # Artifact paths are like "agents/test.md" or "agents/subdir/test.md"
            # We need to strip the type prefix to avoid duplication
            artifact_rel_path = Path(artifact_path)
            type_prefix = f"{artifact_type}s"

            if artifact_rel_path.parts[0] == type_prefix:
                # Strip the type prefix (e.g., "agents/") and keep the rest
                relative_parts = artifact_rel_path.parts[1:]
                if relative_parts:
                    target = target_dir / Path(*relative_parts)
                else:
                    target = target_dir / artifact_rel_path.name
            else:
                # Fallback: use the whole path if prefix doesn't match
                target = target_dir / artifact_rel_path

            # Ensure parent directories exist
            if not target.parent.exists():
                target.parent.mkdir(parents=True, exist_ok=True)

            # Handle conflicts based on policy
            if target.exists():
                if conflict_policy == ConflictPolicy.ERROR:
                    raise FileExistsError(
                        f"Artifact already exists: {target}\nUse --force to overwrite"
                    )
                elif conflict_policy == ConflictPolicy.SKIP:
                    click.echo(f"  Skipping (exists): {target.name}", err=True)
                    continue
                elif conflict_policy == ConflictPolicy.OVERWRITE:
                    click.echo(f"  Overwriting: {target.name}", err=True)
                    # Will overwrite below
                else:
                    raise ValueError(f"Unsupported policy: {conflict_policy}")

            # Write artifact
            target.write_text(content, encoding="utf-8")

            # Log installation with namespace visibility
            relative_path = target.relative_to(claude_dir)
            click.echo(f"  Installed {artifact_type}: {relative_path}", err=True)

            # Track installation
            installed_artifacts.append(str(target.relative_to(project_dir)))

    return InstalledKit(
        kit_id=manifest.name,
        version=manifest.version,
        source=resolved.source,
        installed_at=datetime.now().isoformat(),
        artifacts=installed_artifacts,
        conflict_policy=conflict_policy.value,
    )
