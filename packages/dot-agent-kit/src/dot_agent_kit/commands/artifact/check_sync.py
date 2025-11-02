"""Check sync command for validating bundled kit artifacts."""

from dataclasses import dataclass
from pathlib import Path

import click

from dot_agent_kit.io import load_project_config
from dot_agent_kit.sources import BundledKitSource


@dataclass(frozen=True)
class SyncCheckResult:
    """Result of checking sync status for one artifact."""

    artifact_path: Path
    is_in_sync: bool
    reason: str | None = None


def check_artifact_sync(
    project_dir: Path,
    artifact_rel_path: str,
    bundled_base: Path,
) -> SyncCheckResult:
    """Check if an artifact is in sync with bundled source."""
    # Artifact path in .claude/
    local_path = project_dir / artifact_rel_path

    # Corresponding bundled path (remove .claude/ prefix if present)
    artifact_rel = Path(artifact_rel_path)
    if artifact_rel.parts[0] == ".claude":
        artifact_rel = Path(*artifact_rel.parts[1:])

    bundled_path = bundled_base / artifact_rel

    # Check if both exist
    if not local_path.exists():
        return SyncCheckResult(
            artifact_path=local_path,
            is_in_sync=False,
            reason="Local artifact missing",
        )

    if not bundled_path.exists():
        return SyncCheckResult(
            artifact_path=local_path,
            is_in_sync=False,
            reason="Bundled artifact missing",
        )

    # Compare content
    try:
        local_content = local_path.read_bytes()
        bundled_content = bundled_path.read_bytes()

        if local_content != bundled_content:
            return SyncCheckResult(
                artifact_path=local_path,
                is_in_sync=False,
                reason="Content differs",
            )
    except Exception as e:
        return SyncCheckResult(
            artifact_path=local_path,
            is_in_sync=False,
            reason=f"Read error: {e}",
        )

    return SyncCheckResult(
        artifact_path=local_path,
        is_in_sync=True,
    )


@click.command(name="check-sync")
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed sync status for all artifacts",
)
def check_sync(verbose: bool) -> None:
    """Check if local artifacts are in sync with bundled kit sources.

    This command validates that artifacts in .claude/ match their corresponding
    bundled sources in the dot-agent-kit package data. It's primarily used in
    CI to ensure that bundled kit sources are kept in sync during development.

    Exit codes:
      0 - All artifacts are in sync
      1 - Some artifacts are out of sync or errors occurred
    """
    project_dir = Path.cwd()

    config = load_project_config(project_dir)
    if config is None:
        click.echo("Error: No dot-agent.toml found", err=True)
        raise SystemExit(1)

    if len(config.kits) == 0:
        click.echo("No kits installed")
        return

    bundled_source = BundledKitSource()

    # Check sync for each installed kit from bundled source
    all_results: list[tuple[str, list[SyncCheckResult]]] = []

    for kit_id, installed in config.kits.items():
        # Only check kits from bundled source
        if not bundled_source.can_resolve(installed.source):
            continue

        # Get bundled kit base path
        bundled_path = bundled_source._get_bundled_kit_path(installed.source)
        if bundled_path is None:
            click.echo(f"Warning: Could not find bundled kit: {installed.source}", err=True)
            continue

        # Check each artifact
        kit_results: list[SyncCheckResult] = []
        for artifact_path in installed.artifacts:
            result = check_artifact_sync(project_dir, artifact_path, bundled_path)
            kit_results.append(result)

        all_results.append((kit_id, kit_results))

    if len(all_results) == 0:
        click.echo("No bundled kits found to check")
        return

    # Display results
    total_artifacts = 0
    in_sync_count = 0
    out_of_sync_count = 0

    for kit_id, results in all_results:
        total_artifacts += len(results)
        kit_in_sync = sum(1 for r in results if r.is_in_sync)
        kit_out_of_sync = len(results) - kit_in_sync

        in_sync_count += kit_in_sync
        out_of_sync_count += kit_out_of_sync

        if verbose or kit_out_of_sync > 0:
            click.echo(f"\nKit: {kit_id}")
            for result in results:
                status = "✓" if result.is_in_sync else "✗"
                rel_path = result.artifact_path.relative_to(project_dir)
                click.echo(f"  {status} {rel_path}")

                if not result.is_in_sync and result.reason is not None:
                    click.echo(f"      {result.reason}", err=True)

    # Summary
    click.echo()
    click.echo(f"Checked {total_artifacts} artifact(s) from {len(all_results)} bundled kit(s):")
    click.echo(f"  ✓ In sync: {in_sync_count}")

    if out_of_sync_count > 0:
        click.echo(f"  ✗ Out of sync: {out_of_sync_count}", err=True)
        click.echo()
        click.echo(
            "Run 'dot-agent kit sync --force' to update local artifacts from bundled sources",
            err=True,
        )
        raise SystemExit(1)
    else:
        click.echo()
        click.echo("All bundled kit artifacts are in sync!")
