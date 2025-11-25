"""Artifact validation operations."""

from dataclasses import dataclass
from pathlib import Path

from dot_agent_kit.io.state import load_project_config


@dataclass(frozen=True)
class ValidationResult:
    """Result of artifact validation."""

    artifact_path: Path
    is_valid: bool
    errors: list[str]


def validate_artifact(artifact_path: Path) -> ValidationResult:
    """Validate a single artifact file exists."""
    if not artifact_path.exists():
        return ValidationResult(
            artifact_path=artifact_path,
            is_valid=False,
            errors=["File does not exist"],
        )

    # Simple validation: just check that the file exists and is readable
    try:
        _ = artifact_path.read_text(encoding="utf-8")
        return ValidationResult(
            artifact_path=artifact_path,
            is_valid=True,
            errors=[],
        )
    except Exception as e:
        return ValidationResult(
            artifact_path=artifact_path,
            is_valid=False,
            errors=[f"Cannot read file: {e}"],
        )


def validate_project(project_dir: Path) -> list[ValidationResult]:
    """Validate only managed artifacts (installed from kits) in project."""
    results: list[ValidationResult] = []

    claude_dir = project_dir / ".claude"
    if not claude_dir.exists():
        return results

    # Load config to get list of managed artifacts
    config = load_project_config(project_dir)
    if not config:
        return results

    # Collect all managed artifact paths from all installed kits
    managed_paths: set[str] = set()
    for kit in config.kits.values():
        for artifact_path in kit.artifacts:
            # Normalize path: remove leading ".claude/" if present
            normalized = artifact_path.replace(".claude/", "")
            managed_paths.add(normalized)

    # Validate all managed artifacts
    for managed_path in managed_paths:
        full_path = claude_dir / managed_path
        result = validate_artifact(full_path)
        results.append(result)

    return results
