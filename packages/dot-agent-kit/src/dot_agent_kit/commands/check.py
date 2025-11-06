"""Check command for validating artifacts and sync status."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import click

from dot_agent_kit.hooks.models import ClaudeSettings, HookDefinition
from dot_agent_kit.hooks.settings import extract_kit_id_from_command, load_settings
from dot_agent_kit.io import load_project_config
from dot_agent_kit.io.manifest import load_kit_manifest
from dot_agent_kit.models.config import InstalledKit, ProjectConfig
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


@dataclass(frozen=True)
class InstalledHook:
    """A hook extracted from settings.json."""

    hook_id: str  # Extracted from command or environment variable
    command: str
    timeout: int
    lifecycle: str  # "UserPromptSubmit", etc.


@dataclass(frozen=True)
class HookDriftIssue:
    """A single hook drift issue."""

    severity: Literal["error", "warning"]
    message: str
    expected: str | None
    actual: str | None


@dataclass(frozen=True)
class HookDriftResult:
    """Result of checking hook drift for one kit."""

    kit_id: str
    issues: list[HookDriftIssue]


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


def compare_artifact_lists(
    manifest_artifacts: dict[str, list[str]],
    installed_artifacts: list[str],
) -> tuple[list[str], list[str]]:
    """Compare manifest artifacts against installed artifacts.

    Args:
        manifest_artifacts: Dict of artifact type to list of relative paths from manifest
        installed_artifacts: List of installed artifact paths (relative to project root)

    Returns:
        Tuple of (missing, obsolete) artifact lists
    """
    # Build set of expected paths from manifest
    manifest_paths = set()
    for _artifact_type, paths in manifest_artifacts.items():
        for path in paths:
            # Transform manifest path to installed path
            # Manifest: "commands/gt/land-branch.md"
            # Installed: ".claude/commands/gt/land-branch.md"
            full_path = f".claude/{path}"
            manifest_paths.add(full_path)

    installed_paths = set(installed_artifacts)

    missing = sorted(manifest_paths - installed_paths)
    obsolete = sorted(installed_paths - manifest_paths)

    return missing, obsolete


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


def _extract_hooks_for_kit(
    settings: ClaudeSettings,
    kit_id: str,
    expected_hooks: list[HookDefinition],
) -> list[InstalledHook]:
    """Extract hooks for specific kit from settings.json with strict validation.

    Uses extract_kit_id_from_command() to identify kit ownership.
    Validates extracted hook IDs against expected format and manifest.

    Args:
        settings: Loaded settings object
        kit_id: Kit ID to filter for
        expected_hooks: List of hook definitions from manifest (for validation)

    Returns:
        List of InstalledHook objects for this kit

    Raises:
        ValueError: If hook ID format is invalid (not matching ^[a-z0-9-]+$)
        ValueError: If extracted hook ID is not in expected_hooks list
    """
    results: list[InstalledHook] = []

    if not settings.hooks:
        return results

    for lifecycle, groups in settings.hooks.items():
        for group in groups:
            for hook_entry in group.hooks:
                # Extract kit ID from command
                command_kit_id = extract_kit_id_from_command(hook_entry.command)

                if command_kit_id == kit_id:
                    # Extract hook ID from command
                    # Format: DOT_AGENT_KIT_ID=kit-name DOT_AGENT_HOOK_ID=hook-id python3 ...
                    import re

                    hook_id_match = re.search(r"DOT_AGENT_HOOK_ID=(\S+)", hook_entry.command)
                    if not hook_id_match:
                        raise ValueError(
                            f"Hook command for kit '{kit_id}' is missing "
                            f"DOT_AGENT_HOOK_ID environment variable. "
                            f"Command: {hook_entry.command}"
                        )

                    hook_id = hook_id_match.group(1)

                    # Validate hook ID format (must be lowercase kebab-case)
                    format_pattern = r"^[a-z0-9-]+$"
                    if not re.match(format_pattern, hook_id):
                        raise ValueError(
                            f"Invalid hook ID format: '{hook_id}' for kit '{kit_id}'. "
                            f"Hook IDs must match pattern {format_pattern} "
                            f"(lowercase letters, numbers, and hyphens only)"
                        )

                    # Validate hook ID exists in manifest
                    expected_hook_ids = {hook.id for hook in expected_hooks}
                    if hook_id not in expected_hook_ids:
                        expected_ids_str = ", ".join(f"'{id}'" for id in sorted(expected_hook_ids))
                        raise ValueError(
                            f"Hook ID '{hook_id}' for kit '{kit_id}' not found in manifest. "
                            f"Expected hook IDs: [{expected_ids_str}]"
                        )

                    results.append(
                        InstalledHook(
                            hook_id=hook_id,
                            command=hook_entry.command,
                            timeout=hook_entry.timeout,
                            lifecycle=lifecycle,
                        )
                    )

    return results


def _detect_hook_drift(
    kit_id: str,
    expected_hooks: list[HookDefinition],
    installed_hooks: list[InstalledHook],
) -> HookDriftResult | None:
    """Compare expected hooks against installed hooks.

    Args:
        kit_id: Kit ID being checked
        expected_hooks: Hooks defined in kit.yaml
        installed_hooks: Hooks found in settings.json

    Returns:
        HookDriftResult if drift detected, None if all aligned
    """
    issues: list[HookDriftIssue] = []

    # Build lookup maps
    expected_by_id = {hook.id: hook for hook in expected_hooks}
    installed_by_id = {hook.hook_id: hook for hook in installed_hooks}

    # Check each expected hook
    for expected_hook in expected_hooks:
        if expected_hook.id not in installed_by_id:
            # Missing hook
            issues.append(
                HookDriftIssue(
                    severity="error",
                    message=f"Missing hook: '{expected_hook.id}' not found in settings.json",
                    expected=expected_hook.id,
                    actual=None,
                )
            )
        else:
            # Check if command format matches expectations
            installed = installed_by_id[expected_hook.id]

            # Expected format: "DOT_AGENT_KIT_ID={kit_id} DOT_AGENT_HOOK_ID={hook_id} {invocation}"
            expected_env_prefix = f"DOT_AGENT_KIT_ID={kit_id} DOT_AGENT_HOOK_ID={expected_hook.id}"
            expected_command = f"{expected_env_prefix} {expected_hook.invocation}"

            # Check if command matches expected format
            if installed.command != expected_command:
                issues.append(
                    HookDriftIssue(
                        severity="warning",
                        message=f"Command mismatch for '{expected_hook.id}'",
                        expected=expected_command,
                        actual=installed.command,
                    )
                )

    # Check for obsolete hooks
    for installed_hook in installed_hooks:
        if installed_hook.hook_id not in expected_by_id:
            issues.append(
                HookDriftIssue(
                    severity="warning",
                    message=f"Obsolete hook: '{installed_hook.hook_id}' found in settings.json "
                    f"but not defined in kit.yaml",
                    expected=None,
                    actual=installed_hook.hook_id,
                )
            )

    if len(issues) == 0:
        return None

    return HookDriftResult(kit_id=kit_id, issues=issues)


def validate_hook_configuration(
    project_dir: Path,
    config: ProjectConfig,
) -> list[HookDriftResult]:
    """Check if installed hooks match kit expectations.

    Only validates bundled kits. Skips validation if kit.yaml has no hooks field.

    Args:
        project_dir: Project root directory
        config: Loaded project configuration

    Returns:
        List of HookDriftResult objects (empty if no drift)
    """
    results: list[HookDriftResult] = []

    # Load settings.json
    settings_path = project_dir / ".claude" / "settings.json"
    if not settings_path.exists():
        return results

    settings = load_settings(settings_path)

    bundled_source = BundledKitSource()

    for kit_id, installed_kit in config.kits.items():
        # Only check bundled kits
        if installed_kit.source_type != SOURCE_TYPE_BUNDLED:
            continue

        # Get bundled kit path
        bundled_path = bundled_source._get_bundled_kit_path(kit_id)
        if bundled_path is None:
            continue

        # Load manifest
        manifest_path = bundled_path / "kit.yaml"
        if not manifest_path.exists():
            continue

        manifest = load_kit_manifest(manifest_path)

        # Skip if no hooks defined in manifest
        if not manifest.hooks or len(manifest.hooks) == 0:
            continue

        # Extract installed hooks for this kit
        # If extraction fails (invalid format, hook not in manifest), treat as drift
        try:
            installed_hooks = _extract_hooks_for_kit(settings, kit_id, manifest.hooks)
        except ValueError as e:
            # Hook extraction failed - create an error drift result
            results.append(
                HookDriftResult(
                    kit_id=kit_id,
                    issues=[
                        HookDriftIssue(
                            severity="error",
                            message=str(e),
                            expected=None,
                            actual=None,
                        )
                    ],
                )
            )
            continue

        # Detect drift
        drift_result = _detect_hook_drift(kit_id, manifest.hooks, installed_hooks)

        if drift_result is not None:
            results.append(drift_result)

    return results


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
        all_results: list[tuple[str, list, list[str], list[str]]] = []

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

            # Load manifest and check for missing/obsolete artifacts
            missing_artifacts: list[str] = []
            obsolete_artifacts: list[str] = []

            manifest_path = bundled_path / "kit.yaml"
            if manifest_path.exists():
                manifest = load_kit_manifest(manifest_path)
                missing_artifacts, obsolete_artifacts = compare_artifact_lists(
                    manifest.artifacts,
                    installed.artifacts,
                )

            all_results.append((kit_id_iter, kit_results, missing_artifacts, obsolete_artifacts))

        if len(all_results) == 0:
            click.echo("No bundled kits found to check")
            sync_passed = True
        else:
            # Display results
            total_artifacts = 0
            in_sync_count = 0
            out_of_sync_count = 0
            missing_count = 0
            obsolete_count = 0

            for kit_id_iter, results, missing, obsolete in all_results:
                total_artifacts += len(results)
                kit_in_sync = sum(1 for r in results if r.is_in_sync)
                kit_out_of_sync = len(results) - kit_in_sync

                in_sync_count += kit_in_sync
                out_of_sync_count += kit_out_of_sync
                missing_count += len(missing)
                obsolete_count += len(obsolete)

                has_issues = kit_out_of_sync > 0 or len(missing) > 0 or len(obsolete) > 0
                if verbose or has_issues:
                    click.echo(f"\nKit: {kit_id_iter}")
                    for result in results:
                        status = "✓" if result.is_in_sync else "✗"
                        rel_path = result.artifact_path.relative_to(project_dir)
                        click.echo(f"  {status} {rel_path}")

                        if not result.is_in_sync and result.reason is not None:
                            click.echo(f"      {result.reason}", err=True)

                    # Show missing artifacts
                    if len(missing) > 0:
                        click.echo()
                        click.echo("  Missing artifacts (in manifest but not installed):")
                        for missing_path in missing:
                            click.echo(f"    - {missing_path}", err=True)

                    # Show obsolete artifacts
                    if len(obsolete) > 0:
                        click.echo()
                        click.echo("  Obsolete artifacts (installed but not in manifest):")
                        for obsolete_path in obsolete:
                            click.echo(f"    - {obsolete_path}", err=True)

            # Summary
            click.echo()
            kit_count = len(all_results)
            click.echo(f"Checked {total_artifacts} artifact(s) from {kit_count} bundled kit(s):")
            click.echo(f"  ✓ In sync: {in_sync_count}")

            if out_of_sync_count > 0:
                click.echo(f"  ✗ Out of sync: {out_of_sync_count}", err=True)

            if missing_count > 0:
                click.echo(f"  ⚠ Missing: {missing_count}", err=True)

            if obsolete_count > 0:
                click.echo(f"  ⚠ Obsolete: {obsolete_count}", err=True)

            if out_of_sync_count > 0 or missing_count > 0 or obsolete_count > 0:
                click.echo()
                click.echo("Run 'dot-agent kit sync --force' to update artifacts", err=True)
                sync_passed = False
            else:
                click.echo()
                click.echo("All artifacts are in sync!")
                sync_passed = True

    click.echo()

    # Part 4: Hook configuration validation
    click.echo("=== Hook Configuration Validation ===")

    hook_passed = True
    if not config_exists:
        click.echo("No dot-agent.toml found - skipping hook validation")
    elif len(config.kits) == 0:
        click.echo("No kits installed - skipping hook validation")
    else:
        hook_results = validate_hook_configuration(project_dir, config)

        if len(hook_results) == 0:
            click.echo("No hook drift detected - all hooks are in sync!")
            hook_passed = True
        else:
            # Display drift issues
            for drift_result in hook_results:
                click.echo()
                click.echo(f"Kit: {drift_result.kit_id}")

                for issue in drift_result.issues:
                    status = "✗" if issue.severity == "error" else "⚠"
                    click.echo(f"  {status} {issue.message}", err=True)

                    if issue.expected is not None:
                        click.echo(f"      Expected: {issue.expected}", err=True)
                    if issue.actual is not None:
                        click.echo(f"      Actual:   {issue.actual}", err=True)

            # Summary
            click.echo()
            kit_count = len(hook_results)
            error_count = sum(1 for r in hook_results for i in r.issues if i.severity == "error")
            warning_count = sum(
                1 for r in hook_results for i in r.issues if i.severity == "warning"
            )

            click.echo(f"Checked hook configuration for {kit_count} kit(s):")
            if error_count > 0:
                click.echo(f"  ✗ Errors: {error_count}", err=True)
            if warning_count > 0:
                click.echo(f"  ⚠ Warnings: {warning_count}", err=True)

            click.echo()
            click.echo("Run 'dot-agent kit sync --force' to update hook configuration", err=True)
            hook_passed = False

    # Overall result
    click.echo()
    click.echo("=" * 40)
    if config_passed and validation_passed and sync_passed and hook_passed:
        click.echo("✓ All checks passed!")
    else:
        click.echo("✗ Some checks failed", err=True)
        raise SystemExit(1)
