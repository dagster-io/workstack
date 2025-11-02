"""Sync kit files back to source for development."""

import shutil
from pathlib import Path

import click

from dot_agent_kit.io.state import load_project_config


def get_kit_source_dir(kit_id: str) -> Path:
    """Get the source directory for a kit.

    Args:
        kit_id: The kit identifier

    Returns:
        Path to the kit's source directory
    """
    # Assumes we're in the workstack project structure
    project_root = Path.cwd()
    while project_root.parent != project_root:
        kit_path = (
            project_root
            / "packages"
            / "dot-agent-kit"
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / kit_id
        )
        if kit_path.exists():
            return kit_path
        project_root = project_root.parent

    # Fallback to direct path from current directory
    kit_path = Path("packages/dot-agent-kit/src/dot_agent_kit/data/kits") / kit_id
    if kit_path.exists():
        return kit_path

    raise ValueError(f"Could not find source directory for kit: {kit_id}") from None


def map_artifact_to_source(artifact_path: str, kit_id: str) -> Path:
    """Map an installed artifact path back to its source location.

    Args:
        artifact_path: Installed artifact path (e.g., ".claude/skills/gt-graphite/SKILL.md")
        kit_id: The kit identifier

    Returns:
        Path to the source file in the kit directory
    """
    kit_source_dir = get_kit_source_dir(kit_id)

    # Parse the artifact path
    # Format: .claude/{type}/{name}/{file}
    parts = Path(artifact_path).parts
    if len(parts) < 3 or parts[0] != ".claude":
        raise ValueError(f"Invalid artifact path format: {artifact_path}")

    artifact_type = parts[1]  # e.g., "skills", "commands", "agents"

    # Build source path: kits/{kit_id}/{type}/{rest}
    # Note: artifact_type is already plural (skills, commands, agents)
    rest_parts = parts[2:]  # Everything after .claude/{type}/
    source_path = kit_source_dir / artifact_type / Path(*rest_parts)

    return source_path


def sync_file_to_source(
    installed_path: Path,
    source_path: Path,
    dry_run: bool,
    verbose: bool,
) -> bool:
    """Sync a single file from installed location back to source.

    Args:
        installed_path: Path to installed file
        source_path: Path to source file
        dry_run: If True, only show what would be synced
        verbose: If True, show detailed output

    Returns:
        True if file was synced (or would be synced in dry-run), False otherwise
    """
    if not installed_path.exists():
        if verbose:
            click.echo(f"Skipped (not found): {installed_path}", err=True)
        return False

    if dry_run:
        click.echo(f"Would sync: {installed_path} -> {source_path}")
        return True

    if verbose:
        click.echo(f"Syncing: {installed_path} -> {source_path}")

    # Ensure parent directory exists
    source_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy file
    shutil.copy2(installed_path, source_path)
    return True


def sync_directory_to_source(
    installed_dir: Path,
    source_dir: Path,
    dry_run: bool,
    verbose: bool,
) -> int:
    """Recursively sync a directory from installed location back to source.

    Args:
        installed_dir: Path to installed directory
        source_dir: Path to source directory
        dry_run: If True, only show what would be synced
        verbose: If True, show detailed output

    Returns:
        Number of files synced
    """
    if not installed_dir.exists():
        return 0

    if not installed_dir.is_dir():
        return 0

    synced_count = 0

    for item in installed_dir.rglob("*"):
        if not item.is_file():
            continue

        # Compute relative path and corresponding source path
        rel_path = item.relative_to(installed_dir)
        source_path = source_dir / rel_path

        if sync_file_to_source(item, source_path, dry_run, verbose):
            synced_count += 1

    return synced_count


def sync_kit_artifacts(
    kit_id: str,
    artifacts: list[str],
    project_dir: Path,
    dry_run: bool,
    verbose: bool,
) -> int:
    """Sync all artifacts for a kit back to source.

    Args:
        kit_id: The kit identifier
        artifacts: List of artifact paths to sync
        project_dir: Project directory path
        dry_run: If True, only show what would be synced
        verbose: If True, show detailed output

    Returns:
        Number of files synced
    """
    synced_count = 0

    for artifact_path in artifacts:
        installed_path = project_dir / artifact_path
        source_path = map_artifact_to_source(artifact_path, kit_id)

        # Sync the main artifact file
        if sync_file_to_source(installed_path, source_path, dry_run, verbose):
            synced_count += 1

        # Check for subdirectories (references/, scripts/) and sync them too
        installed_parent = installed_path.parent
        if installed_parent.exists() and installed_parent.is_dir():
            for subdir_name in ["references", "scripts"]:
                subdir = installed_parent / subdir_name
                if subdir.exists() and subdir.is_dir():
                    source_subdir = source_path.parent / subdir_name
                    synced_count += sync_directory_to_source(
                        subdir,
                        source_subdir,
                        dry_run,
                        verbose,
                    )

    return synced_count


@click.command(name="kit-sync-back")
@click.option("--kit", "kit_filter", help="Sync only this specific kit")
@click.option("--dry-run", is_flag=True, help="Show what would be synced without making changes")
@click.option("--verbose", is_flag=True, help="Show detailed output")
def kit_sync_back_command(kit_filter: str | None, dry_run: bool, verbose: bool) -> None:
    """Sync kit files from .claude/ back to their source in packages/dot-agent-kit/.

    This is useful when editing kit files in place during development. After making
    changes to kit files in .claude/, run this command to copy them back to the kit
    source directory.

    Examples:
        workstack-dev kit-sync-back                    # Sync all kits
        workstack-dev kit-sync-back --kit gt           # Sync only the gt kit
        workstack-dev kit-sync-back --dry-run          # Preview changes
    """
    project_dir = Path.cwd()

    # Load project configuration
    config = load_project_config(project_dir)
    if config is None:
        click.echo("Error: No dot-agent.toml found in current directory", err=True)
        raise SystemExit(1)

    if not config.kits:
        click.echo("No kits installed", err=True)
        raise SystemExit(0)

    # Filter kits if specified
    if kit_filter:
        if kit_filter not in config.kits:
            click.echo(f"Error: Kit '{kit_filter}' is not installed", err=True)
            available = ", ".join(config.kits.keys())
            click.echo(f"Available kits: {available}", err=True)
            raise SystemExit(1)
        kits_to_sync = {kit_filter: config.kits[kit_filter]}
    else:
        kits_to_sync = config.kits

    # Sync each kit
    total_synced = 0
    for kit_id, installed_kit in kits_to_sync.items():
        if verbose or len(kits_to_sync) > 1:
            click.echo(f"\nSyncing kit: {kit_id}")

        try:
            synced = sync_kit_artifacts(
                kit_id,
                installed_kit.artifacts,
                project_dir,
                dry_run,
                verbose,
            )
            total_synced += synced

            if verbose or len(kits_to_sync) > 1:
                click.echo(f"  {synced} file(s) synced")
        except ValueError as e:
            click.echo(f"Error syncing kit '{kit_id}': {e}", err=True)
            raise SystemExit(1) from e

    # Summary
    if dry_run:
        click.echo(f"\nWould sync {total_synced} file(s) total")
    else:
        click.echo(f"\nSynced {total_synced} file(s) total")
