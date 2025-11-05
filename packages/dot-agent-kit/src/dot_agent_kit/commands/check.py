"""Check command for validating artifacts and sync status."""

from dataclasses import dataclass
from pathlib import Path

import click

from dot_agent_kit.io import load_project_config
from dot_agent_kit.models.config import InstalledKit
from dot_agent_kit.models.types import SOURCE_TYPE_BUNDLED, SOURCE_TYPE_PACKAGE
from dot_agent_kit.operations import validate_project
from dot_agent_kit.sources import BundledKitSource


@dataclass(frozen=True)
class SyncCheckResult:
    """Result of checking sync status for one artifact."""

    artifact_path: Path
    is_in_sync: bool
    reason: str | None = None


@dataclass(frozen=True)
class ConfigValidationResult:
    """Result of validating configuration fields for one kit."""

    kit_id: str
    is_valid: bool
    errors: list[str]


def validate_kit_fields(kit: InstalledKit) -> list[str]:
    """Validate all fields of an installed kit using LBYL checks.

    Args:
        kit: InstalledKit to validate

    Returns:
        List of error messages (empty if all valid)
    """
    errors = []

    # Validate kit_id is non-empty
    if not kit.kit_id:
        errors.append("kit_id is empty")

    # Validate source_type is valid
    if kit.source_type not in [SOURCE_TYPE_BUNDLED, SOURCE_TYPE_PACKAGE]:
        msg = (
            f"Invalid source_type: {kit.source_type}. "
            f"Must be '{SOURCE_TYPE_BUNDLED}' or '{SOURCE_TYPE_PACKAGE}'"
        )
        errors.append(msg)

    # Validate version is non-empty
    if not kit.version:
        errors.append("version is empty")

    # Validate artifacts list is non-empty
    if not kit.artifacts:
        errors.append("artifacts list is empty")

    # Validate installed_at is non-empty (basic check)
    # More sophisticated ISO 8601 parsing could be added if needed
    if not kit.installed_at:
        errors.append("installed_at is empty")

    return errors


def validate_configuration(
    config_kits: dict[str, InstalledKit],
) -> list[ConfigValidationResult]:
    """Validate all installed kits in configuration.

    Args:
        config_kits: Dictionary of kit_id to InstalledKit

    Returns:
        List of validation results for each kit
    """
    results = []

    for kit_id, installed_kit in config_kits.items():
        field_errors = validate_kit_fields(installed_kit)

        result = ConfigValidationResult(
            kit_id=kit_id,
            is_valid=len(field_errors) == 0,
            errors=field_errors,
        )
        results.append(result)

    return results


def check_artifact_sync(
    project_dir: Path,
    artifact_rel_path: str,
    bundled_base: Path,
) -> SyncCheckResult:
    """Check if an artifact is in sync with bundled source."""
    # Normalize artifact path: remove .claude/ prefix if present
    normalized_path = artifact_rel_path.replace(".claude/", "")

    # Artifact path in .claude/
    local_path = project_dir / ".claude" / normalized_path

    # Corresponding bundled path
    bundled_path = bundled_base / normalized_path

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
    local_content = local_path.read_bytes()
    bundled_content = bundled_path.read_bytes()

    if local_content != bundled_content:
        return SyncCheckResult(
            artifact_path=local_path,
            is_in_sync=False,
            reason="Content differs",
        )

    return SyncCheckResult(
        artifact_path=local_path,
        is_in_sync=True,
    )


@click.command()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed validation information",
)
def check(verbose: bool) -> None:
    """Validate installed artifacts and check bundled kit sync status."""
    project_dir = Path.cwd()

    # Check if config exists
    config = load_project_config(project_dir)
    config_exists = config is not None

    # Part 1: Validate configuration
    click.echo("=== Configuration Validation ===")

    # Check if there are kits to validate
    if not config_exists or len(config.kits) == 0:
        click.echo("No kits installed - skipping configuration validation")
        config_passed = True
    else:
        # Validate all installed kits
        validation_results = validate_configuration(config.kits)
        valid_count = sum(1 for r in validation_results if r.is_valid)
        invalid_count = len(validation_results) - valid_count

        # Show results
        if verbose or invalid_count > 0:
            for result in validation_results:
                status = "✓" if result.is_valid else "✗"
                click.echo(f"{status} {result.kit_id}")

                if not result.is_valid:
                    for error in result.errors:
                        click.echo(f"  - {error}", err=True)

        # Summary
        click.echo()
        click.echo(f"Validated {len(validation_results)} kit configuration(s):")
        click.echo(f"  ✓ Valid: {valid_count}")

        if invalid_count > 0:
            click.echo(f"  ✗ Invalid: {invalid_count}", err=True)
            config_passed = False
        else:
            click.echo("All kit configurations are valid!")
            config_passed = True

    click.echo()

    # Part 2: Validate artifacts
    click.echo("=== Artifact Validation ===")
    validation_results = validate_project(project_dir)

    if len(validation_results) == 0:
        click.echo("No artifacts found to validate")
        validation_passed = True
    else:
        valid_count = sum(1 for r in validation_results if r.is_valid)
        invalid_count = len(validation_results) - valid_count

        # Show results
        if verbose or invalid_count > 0:
            for result in validation_results:
                status = "✓" if result.is_valid else "✗"
                rel_path = result.artifact_path.relative_to(project_dir)
                click.echo(f"{status} {rel_path}")

                if not result.is_valid:
                    for error in result.errors:
                        click.echo(f"  - {error}", err=True)

        # Summary
        click.echo()
        click.echo(f"Validated {len(validation_results)} artifacts:")
        click.echo(f"  ✓ Valid: {valid_count}")

        if invalid_count > 0:
            click.echo(f"  ✗ Invalid: {invalid_count}", err=True)
            validation_passed = False
        else:
            click.echo("All artifacts are valid!")
            validation_passed = True

    click.echo()

    # Part 3: Check bundled kit sync status
    click.echo("=== Bundled Kit Sync Status ===")

    sync_passed = True
    if not config_exists:
        click.echo("No dot-agent.toml found - skipping sync check")
    elif len(config.kits) == 0:
        click.echo("No kits installed - skipping sync check")
    else:
        bundled_source = BundledKitSource()
        all_results: list[tuple[str, list]] = []

        for kit_id_iter, installed in config.kits.items():
            # Only check kits from bundled source
            if installed.source_type != SOURCE_TYPE_BUNDLED:
                continue

            # Get bundled kit base path
            bundled_path = bundled_source._get_bundled_kit_path(installed.kit_id)
            if bundled_path is None:
                click.echo(f"Warning: Could not find bundled kit: {installed.kit_id}", err=True)
                continue

            # Check each artifact
            kit_results = []
            for artifact_path in installed.artifacts:
                result = check_artifact_sync(project_dir, artifact_path, bundled_path)
                kit_results.append(result)

            all_results.append((kit_id_iter, kit_results))

        if len(all_results) == 0:
            click.echo("No bundled kits found to check")
            sync_passed = True
        else:
            # Display results
            total_artifacts = 0
            in_sync_count = 0
            out_of_sync_count = 0

            for kit_id_iter, results in all_results:
                total_artifacts += len(results)
                kit_in_sync = sum(1 for r in results if r.is_in_sync)
                kit_out_of_sync = len(results) - kit_in_sync

                in_sync_count += kit_in_sync
                out_of_sync_count += kit_out_of_sync

                if verbose or kit_out_of_sync > 0:
                    click.echo(f"\nKit: {kit_id_iter}")
                    for result in results:
                        status = "✓" if result.is_in_sync else "✗"
                        rel_path = result.artifact_path.relative_to(project_dir)
                        click.echo(f"  {status} {rel_path}")

                        if not result.is_in_sync and result.reason is not None:
                            click.echo(f"      {result.reason}", err=True)

            # Summary
            click.echo()
            kit_count = len(all_results)
            click.echo(f"Checked {total_artifacts} artifact(s) from {kit_count} bundled kit(s):")
            click.echo(f"  ✓ In sync: {in_sync_count}")

            if out_of_sync_count > 0:
                click.echo(f"  ✗ Out of sync: {out_of_sync_count}", err=True)
                click.echo()
                sync_msg = "Run 'dot-agent kit sync --force' to update local artifacts"
                click.echo(sync_msg, err=True)
                sync_passed = False
            else:
                click.echo()
                click.echo("All artifacts are in sync!")
                sync_passed = True

    # Overall result
    click.echo()
    click.echo("=" * 40)
    if config_passed and validation_passed and sync_passed:
        click.echo("✓ All checks passed!")
    else:
        click.echo("✗ Some checks failed", err=True)
        raise SystemExit(1)
