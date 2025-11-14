"""Registry management commands."""

from pathlib import Path

import click

from dot_agent_kit.cli.output import user_output
from dot_agent_kit.io import require_project_config
from dot_agent_kit.io.registry import rebuild_registry


@click.group()
def registry() -> None:
    """Manage kit documentation registry.

    Commands for managing the kit documentation registry that provides
    agent-facing documentation for installed kits.
    """


@registry.command()
def rebuild() -> None:
    """Regenerate registry from installed kits.

    This command rebuilds the entire kit registry from scratch based on
    currently installed kits. Useful if registry gets out of sync.
    """
    project_dir = Path.cwd()
    config = require_project_config(project_dir)

    user_output("Rebuilding registry from installed kits...")

    try:
        rebuild_registry(project_dir, config)
        user_output("✓ Registry rebuilt successfully")
    except Exception as e:
        user_output(f"Error: Failed to rebuild registry: {e!s}")
        raise SystemExit(1) from e


@registry.command()
def show() -> None:
    """Display current registry contents.

    Shows the contents of the kit-registry.md file, which aggregates
    all installed kit documentation entries.
    """
    project_dir = Path.cwd()
    registry_path = project_dir / ".claude" / "docs" / "kit-registry.md"

    if not registry_path.exists():
        user_output("No registry found")
        user_output("Run 'dot-agent kit registry rebuild' to create the registry")
        raise SystemExit(1)

    content = registry_path.read_text(encoding="utf-8")
    click.echo(content)


@registry.command()
def validate() -> None:
    """Verify registry matches installed kits.

    Checks that:
    - All installed kits have registry entries
    - All registry entries correspond to installed kits
    - Registry entry files exist and are readable
    """
    project_dir = Path.cwd()
    config = require_project_config(project_dir)
    registry_path = project_dir / ".claude" / "docs" / "kit-registry.md"

    # Check registry file exists
    if not registry_path.exists():
        user_output("❌ Registry file not found: .claude/docs/kit-registry.md")
        user_output("Run 'dot-agent kit registry rebuild' to create it")
        raise SystemExit(1)

    # Read registry content
    content = registry_path.read_text(encoding="utf-8")
    registry_lines = [line.strip() for line in content.split("\n") if line.startswith("@")]

    # Extract kit IDs from registry @-includes
    registry_kits = set()
    for line in registry_lines:
        # Parse: @.agent/kits/{kit_id}/registry-entry.md
        if line.startswith("@.agent/kits/") and line.endswith("/registry-entry.md"):
            kit_id = line.split("/")[2]
            registry_kits.add(kit_id)

    # Get installed kit IDs
    installed_kits = set(config.kits.keys())

    # Check for mismatches
    missing_from_registry = installed_kits - registry_kits
    extra_in_registry = registry_kits - installed_kits

    issues = []

    if missing_from_registry:
        issues.append(
            f"Installed kits missing from registry: {', '.join(sorted(missing_from_registry))}"
        )

    if extra_in_registry:
        issues.append(
            f"Registry entries for uninstalled kits: {', '.join(sorted(extra_in_registry))}"
        )

    # Check that registry entry files exist
    for kit_id in registry_kits:
        entry_path = project_dir / ".agent" / "kits" / kit_id / "registry-entry.md"
        if not entry_path.exists():
            issues.append(f"Registry entry file missing for {kit_id}: {entry_path}")

    if issues:
        user_output("❌ Registry validation failed:")
        for issue in issues:
            user_output(f"  - {issue}")
        user_output("\nRun 'dot-agent kit registry rebuild' to fix these issues")
        raise SystemExit(1)

    user_output(f"✓ Registry valid: {len(installed_kits)} kit(s) properly registered")
