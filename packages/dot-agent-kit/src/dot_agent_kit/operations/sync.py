"""Sync operations for kits."""

from dataclasses import dataclass
from pathlib import Path

from dot_agent_kit.io import load_kit_manifest
from dot_agent_kit.models import ConflictPolicy, InstalledKit, ProjectConfig
from dot_agent_kit.operations.install import install_kit
from dot_agent_kit.sources import KitResolver, ResolvedKit


@dataclass(frozen=True)
class SyncResult:
    """Result of syncing a kit."""

    kit_id: str
    old_version: str
    new_version: str
    was_updated: bool
    artifacts_updated: int
    updated_kit: InstalledKit | None = None


def check_for_updates(
    installed: InstalledKit,
    resolver: KitResolver,
    force: bool = False,
) -> tuple[bool, ResolvedKit | None]:
    """Check if an installed kit has updates available.

    Args:
        installed: The currently installed kit
        resolver: Kit resolver to find the source
        force: If True, always return True (forces reinstall regardless of version)
    """
    try:
        resolved = resolver.resolve(installed.source)
    except ValueError:
        # Source no longer available
        return False, None

    if force:
        # Force mode: always consider as having an update
        return True, resolved

    manifest = load_kit_manifest(resolved.manifest_path)

    # Simple version comparison (should use semver in production)
    has_update = manifest.version != installed.version

    return has_update, resolved


def sync_kit(
    kit_id: str,
    installed: InstalledKit,
    resolved: ResolvedKit,
    project_dir: Path,
    force: bool = False,
) -> SyncResult:
    """Sync an installed kit with its source.

    Args:
        kit_id: The kit identifier
        installed: The currently installed kit
        resolved: The resolved kit from the source
        project_dir: Project directory path
        force: If True, reinstall even if versions match
    """
    old_version = installed.version
    manifest = load_kit_manifest(resolved.manifest_path)
    new_version = manifest.version

    if old_version == new_version and not force:
        return SyncResult(
            kit_id=kit_id,
            old_version=old_version,
            new_version=new_version,
            was_updated=False,
            artifacts_updated=0,
            updated_kit=None,
        )

    # Remove old artifacts
    for artifact_path in installed.artifacts:
        full_path = project_dir / artifact_path
        if full_path.exists():
            full_path.unlink()

    # Install new version with OVERWRITE policy
    new_installed = install_kit(
        resolved,
        project_dir,
        conflict_policy=ConflictPolicy.OVERWRITE,
    )

    return SyncResult(
        kit_id=kit_id,
        old_version=old_version,
        new_version=new_version,
        was_updated=True,
        artifacts_updated=len(new_installed.artifacts),
        updated_kit=new_installed,
    )


def sync_all_kits(
    config: ProjectConfig,
    project_dir: Path,
    resolver: KitResolver,
    force: bool = False,
) -> list[SyncResult]:
    """Sync all installed kits.

    Args:
        config: Project configuration
        project_dir: Project directory path
        resolver: Kit resolver
        force: If True, reinstall even if versions match
    """
    results: list[SyncResult] = []

    for kit_id, installed in config.kits.items():
        has_update, resolved = check_for_updates(installed, resolver, force=force)

        if not has_update or resolved is None:
            results.append(
                SyncResult(
                    kit_id=kit_id,
                    old_version=installed.version,
                    new_version=installed.version,
                    was_updated=False,
                    artifacts_updated=0,
                    updated_kit=None,
                )
            )
            continue

        result = sync_kit(kit_id, installed, resolved, project_dir, force=force)
        results.append(result)

    return results
