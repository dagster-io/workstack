"""Test that all bundled kit artifact files are properly declared in kit.yaml manifests.

This test prevents the issue where artifact files exist in the kit source directory
but are missing from the kit.yaml manifest's artifacts section, which would cause
them not to be installed.
"""

from pathlib import Path

from dot_agent_kit.io.manifest import load_kit_manifest


def _get_bundled_kits_dir() -> Path:
    """Get the bundled kits directory path.

    Returns:
        Path to the bundled kits directory
    """
    # Navigate from test file to bundled kits directory
    test_file = Path(__file__)
    repo_root = test_file.parent.parent.parent.parent.parent
    kits_dir = repo_root / "packages" / "dot-agent-kit" / "src" / "dot_agent_kit" / "data" / "kits"

    if not kits_dir.exists():
        msg = f"Bundled kits directory not found at {kits_dir}"
        raise RuntimeError(msg)

    return kits_dir


def _discover_artifact_files(kit_dir: Path) -> set[str]:
    """Discover all artifact files in a kit directory.

    Scans the standard artifact directories (commands/, agents/, skills/, docs/)
    and returns relative paths from the kit directory.

    Args:
        kit_dir: Path to the kit directory containing kit.yaml

    Returns:
        Set of relative paths (e.g., "commands/erk/foo.md")
    """
    artifact_dirs = ["commands", "agents", "skills", "docs"]
    discovered: set[str] = set()

    for dir_name in artifact_dirs:
        artifact_dir = kit_dir / dir_name
        if not artifact_dir.exists():
            continue

        # Find all .md files recursively
        for artifact_file in artifact_dir.rglob("*.md"):
            # Get relative path from kit directory
            rel_path = artifact_file.relative_to(kit_dir)
            discovered.add(str(rel_path.as_posix()))

    return discovered


def _get_manifested_artifacts(manifest_path: Path) -> set[str]:
    """Get all artifacts declared in a kit.yaml manifest.

    Args:
        manifest_path: Path to kit.yaml file

    Returns:
        Set of artifact paths from the manifest
    """
    manifest = load_kit_manifest(manifest_path)

    manifested: set[str] = set()
    for artifact_list in manifest.artifacts.values():
        manifested.update(artifact_list)

    return manifested


def test_all_bundled_kit_artifacts_are_manifested() -> None:
    """Test that every artifact file in bundled kits is declared in kit.yaml.

    This ensures that when kits are installed, all intended artifact files
    get symlinked into the user's .claude/ directory. Missing entries in
    the manifest result in orphaned files that don't get installed.
    """
    kits_dir = _get_bundled_kits_dir()

    # Scan all kit directories
    all_missing: dict[str, list[str]] = {}

    for kit_dir in kits_dir.iterdir():
        if not kit_dir.is_dir():
            continue

        # Skip __pycache__ and other non-kit directories
        if kit_dir.name.startswith("_") or kit_dir.name.startswith("."):
            continue

        manifest_path = kit_dir / "kit.yaml"
        if not manifest_path.exists():
            continue

        # Discover actual artifact files
        discovered = _discover_artifact_files(kit_dir)

        # Get manifested artifacts
        manifested = _get_manifested_artifacts(manifest_path)

        # Find missing artifacts
        missing = discovered - manifested

        if missing:
            all_missing[kit_dir.name] = sorted(missing)

    # Build detailed error message if any artifacts are missing
    if all_missing:
        error_parts = [
            "\nThe following bundled kit artifact files exist but are NOT declared "
            "in their kit.yaml manifests:\n"
        ]

        for kit_name, missing_files in sorted(all_missing.items()):
            error_parts.append(f"\nKit: {kit_name}")
            for file_path in missing_files:
                error_parts.append(f"  - {file_path}")

            # Show where to add these
            manifest_path = kits_dir / kit_name / "kit.yaml"
            error_parts.append(f"\nAdd these to: {manifest_path}")
            error_parts.append(
                "Under the appropriate artifacts section (command, skill, agent, or doc)\n"
            )

        error_message = "\n".join(error_parts)
        raise AssertionError(error_message)
