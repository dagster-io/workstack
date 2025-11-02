"""Artifact validation operations."""

from dataclasses import dataclass
from pathlib import Path

from dot_agent_kit.io import load_project_config, parse_frontmatter, validate_frontmatter


@dataclass(frozen=True)
class ValidationResult:
    """Result of artifact validation."""

    artifact_path: Path
    is_valid: bool
    errors: list[str]


def validate_artifact(artifact_path: Path) -> ValidationResult:
    """Validate a single artifact file."""
    if not artifact_path.exists():
        return ValidationResult(
            artifact_path=artifact_path,
            is_valid=False,
            errors=["File does not exist"],
        )

    content = artifact_path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(content)

    if frontmatter is None:
        return ValidationResult(
            artifact_path=artifact_path,
            is_valid=False,
            errors=["No frontmatter found"],
        )

    errors = validate_frontmatter(frontmatter)

    return ValidationResult(
        artifact_path=artifact_path,
        is_valid=len(errors) == 0,
        errors=errors,
    )


def validate_project(project_dir: Path) -> list[ValidationResult]:
    """Validate all kit artifacts in project.

    Only validates artifacts that were installed from kits, not project-level artifacts.
    """
    results: list[ValidationResult] = []

    # Load config to get kit artifacts
    config = load_project_config(project_dir)
    if config is None:
        return results

    # Collect all kit artifact paths
    kit_artifact_paths: set[Path] = set()
    for installed_kit in config.kits.values():
        for artifact_rel_path in installed_kit.artifacts:
            # Convert relative path to absolute
            artifact_path = project_dir / artifact_rel_path
            kit_artifact_paths.add(artifact_path)

    # Validate only kit artifacts
    for artifact_path in kit_artifact_paths:
        result = validate_artifact(artifact_path)
        results.append(result)

    return results
