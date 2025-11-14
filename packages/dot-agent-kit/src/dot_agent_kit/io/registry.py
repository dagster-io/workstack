"""Registry I/O."""

import re
import shutil
from pathlib import Path

import yaml

from dot_agent_kit.models import InstalledKit, KitManifest, ProjectConfig, RegistryEntry


def load_registry() -> list[RegistryEntry]:
    """Load registry.yaml from package data."""
    # Use importlib.resources to load from package data
    registry_path = Path(__file__).parent.parent / "data" / "registry.yaml"

    with open(registry_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "kits" not in data:
        return []

    return [
        RegistryEntry(
            kit_id=kit["kit_id"],
            source_type=kit["source_type"],
            description=kit["description"],
            version=kit["version"],
        )
        for kit in data["kits"]
    ]


def _validate_registry_entry(entry: str) -> None:
    """Validate registry entry has required fields.

    Required:
    - Header with kit name and version (### kit-name (vX.Y.Z))
    - **Purpose**: line
    - **Usage**: line

    Args:
        entry: Registry entry markdown string

    Raises:
        ValueError: If required fields are missing
    """
    if not re.search(r"^### \S+ \(v\d+\.\d+\.\d+\)$", entry, re.MULTILINE):
        raise ValueError("Registry entry missing required header: ### kit-name (vX.Y.Z)")
    if "**Purpose**:" not in entry:
        raise ValueError("Registry entry missing required field: **Purpose**:")
    if "**Usage**:" not in entry:
        raise ValueError("Registry entry missing required field: **Usage**:")


def generate_registry_entry(
    kit_id: str, version: str, manifest: KitManifest, installed_kit: InstalledKit
) -> str:
    """Generate registry entry markdown from kit manifest.

    Args:
        kit_id: Kit identifier
        version: Kit version
        manifest: Kit manifest data
        installed_kit: Installed kit information

    Returns:
        Formatted markdown string (~15-20 lines)

    Raises:
        ValueError: If required fields are missing from manifest
    """
    # Start with header
    lines = [f"### {kit_id} (v{version})", ""]

    # Add purpose from manifest description
    lines.append(f"**Purpose**: {manifest.description}")
    lines.append("")

    # List artifacts by type
    if manifest.artifacts:
        lines.append("**Artifacts**:")
        for artifact_type, paths in manifest.artifacts.items():
            if paths:
                lines.append(f"- {artifact_type}: {', '.join(paths)}")
        lines.append("")

    # Generate usage example based on artifact types
    lines.append("**Usage**:")
    usage_examples = []

    if "agent" in manifest.artifacts and manifest.artifacts["agent"]:
        agent_name = manifest.artifacts["agent"][0].split("/")[1]  # Extract name from path
        usage_examples.append(f"- Use Task tool with subagent_type=\"{agent_name}\"")

    if "command" in manifest.artifacts and manifest.artifacts["command"]:
        cmd_name = manifest.artifacts["command"][0].split("/")[1]  # Extract name from path
        usage_examples.append(f"- Run `/{cmd_name}` command")

    if "skill" in manifest.artifacts and manifest.artifacts["skill"]:
        skill_name = manifest.artifacts["skill"][0].split("/")[1]  # Extract name from path
        usage_examples.append(f"- Load `{skill_name}` skill")

    # If no usage examples, provide generic guidance based on artifact types
    if not usage_examples:
        if "doc" in manifest.artifacts and manifest.artifacts["doc"]:
            usage_examples.append("- Reference documentation loaded automatically via AGENTS.md")
        else:
            usage_examples.append("- See kit documentation for usage details")

    lines.extend(usage_examples)
    lines.append("")

    entry = "\n".join(lines)

    # Validate before returning
    _validate_registry_entry(entry)

    return entry


def create_kit_registry_file(kit_id: str, entry_content: str, project_dir: Path) -> Path:
    """Create or update registry entry file for a kit.

    Args:
        kit_id: Kit identifier
        entry_content: Registry entry markdown content
        project_dir: Project root directory

    Returns:
        Path to created registry entry file

    Raises:
        IOError: If file cannot be created
    """
    registry_dir = project_dir / ".agent" / "kits" / kit_id

    # Create directory if it doesn't exist
    if not registry_dir.exists():
        registry_dir.mkdir(parents=True, exist_ok=True)

    # Write registry entry file
    registry_file = registry_dir / "registry-entry.md"
    registry_file.write_text(entry_content, encoding="utf-8")

    return registry_file


def add_kit_to_registry(kit_id: str, project_dir: Path) -> None:
    """Add kit @-include to kit-registry.md.

    Args:
        kit_id: Kit identifier
        project_dir: Project root directory

    Raises:
        IOError: If registry file cannot be written
    """
    registry_path = project_dir / ".claude" / "docs" / "kit-registry.md"

    # Create registry file if it doesn't exist
    if not registry_path.exists():
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(
            "# Kit Documentation Registry\n\n"
            "<!-- AUTO-GENERATED: This file is managed by dot-agent kit commands -->\n"
            "<!-- Aggregates all installed kit documentation pointers via @-includes -->\n\n",
            encoding="utf-8",
        )

    # Read current content
    content = registry_path.read_text(encoding="utf-8")

    # Check if @-include already exists
    include_line = f"@.agent/kits/{kit_id}/registry-entry.md"
    if include_line in content:
        return  # Already present

    # Append @-include with blank line before it
    if not content.endswith("\n\n"):
        if content.endswith("\n"):
            content += "\n"
        else:
            content += "\n\n"

    content += f"{include_line}\n"

    # Write updated content
    registry_path.write_text(content, encoding="utf-8")


def remove_kit_from_registry(kit_id: str, project_dir: Path) -> None:
    """Remove kit from registry and delete its registry files.

    Args:
        kit_id: Kit identifier
        project_dir: Project root directory

    Note:
        Logs warning if registry line not found but continues with directory deletion
    """
    registry_path = project_dir / ".claude" / "docs" / "kit-registry.md"

    # Remove @-include line from registry if it exists
    if registry_path.exists():
        content = registry_path.read_text(encoding="utf-8")
        include_line = f"@.agent/kits/{kit_id}/registry-entry.md"

        # Remove the line and any preceding blank line
        lines = content.split("\n")
        filtered_lines = []
        skip_next_blank = False

        for i, line in enumerate(lines):
            if line == include_line:
                # Remove this line and any preceding blank line
                if filtered_lines and not filtered_lines[-1].strip():
                    filtered_lines.pop()
                skip_next_blank = False
                continue
            filtered_lines.append(line)

        registry_path.write_text("\n".join(filtered_lines), encoding="utf-8")

    # Delete kit registry directory
    kit_registry_dir = project_dir / ".agent" / "kits" / kit_id
    if kit_registry_dir.exists():
        shutil.rmtree(kit_registry_dir)


def rebuild_registry(project_dir: Path, config: ProjectConfig) -> None:
    """Rebuild entire registry from installed kits.

    Args:
        project_dir: Project root directory
        config: Project configuration with installed kits

    Raises:
        Exception: With list of kits that failed regeneration
    """
    from dot_agent_kit.io.manifest import load_kit_manifest
    from dot_agent_kit.sources import BundledKitSource, KitResolver, StandalonePackageSource

    registry_path = project_dir / ".claude" / "docs" / "kit-registry.md"

    # Delete existing registry
    if registry_path.exists():
        registry_path.unlink()

    # Create fresh registry with header
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        "# Kit Documentation Registry\n\n"
        "<!-- AUTO-GENERATED: This file is managed by dot-agent kit commands -->\n"
        "<!-- Aggregates all installed kit documentation pointers via @-includes -->\n\n",
        encoding="utf-8",
    )

    failures = []

    # Create resolver to locate kit manifests
    sources = [BundledKitSource(), StandalonePackageSource()]
    resolver = KitResolver(sources)

    # Regenerate entry for each installed kit
    for kit_id, installed_kit in config.kits.items():
        try:
            # Resolve kit to get manifest path
            resolved = resolver.resolve(kit_id)
            if resolved is None:
                failures.append(f"{kit_id}: could not resolve kit")
                continue

            manifest = load_kit_manifest(resolved.manifest_path)
            entry_content = generate_registry_entry(
                kit_id, installed_kit.version, manifest, installed_kit
            )
            create_kit_registry_file(kit_id, entry_content, project_dir)
            add_kit_to_registry(kit_id, project_dir)
        except Exception as e:
            failures.append(f"{kit_id}: {e!s}")

    if failures:
        raise Exception(f"Failed to regenerate registry for some kits:\n" + "\n".join(failures))
