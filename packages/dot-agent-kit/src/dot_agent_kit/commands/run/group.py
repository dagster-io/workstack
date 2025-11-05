"""Run commands from bundled kits."""

import importlib
from pathlib import Path
from typing import Any

import click

from dot_agent_kit.io import load_kit_manifest
from dot_agent_kit.sources.bundled import BundledKitSource


@click.group()
def run_group() -> None:
    """Run executable commands from bundled kits.

    Lists available kits with commands. Use 'dot-agent run <kit_id> --help'
    to see available commands for a specific kit.
    """


def _create_kit_group(kit_name: str, manifest_name: str) -> Any:
    """Create a Click group for a kit's commands."""

    @click.group(name=manifest_name)
    def kit_command_group() -> None:
        """Commands for kit."""

    return kit_command_group


def _load_kit_commands() -> None:
    """Dynamically load commands from all kits with commands."""
    source = BundledKitSource()
    available_kits = source.list_available()

    # Get the kits data directory
    data_dir = Path(__file__).parent.parent.parent / "data" / "kits"

    for kit_name in available_kits:
        kit_dir = data_dir / kit_name
        manifest_path = kit_dir / "kit.yaml"

        if not manifest_path.exists():
            continue

        manifest = load_kit_manifest(manifest_path)

        # Skip kits without commands
        if not manifest.commands:
            continue

        # Create a Click group for this kit
        kit_command_group = _create_kit_group(kit_name, manifest.name)

        # For each command in the kit's manifest
        for command_def in manifest.commands:
            # Convert path to module path
            # Example: commands/check_lbyl.py -> commands.check_lbyl
            module_path_str = command_def.path.replace("/", ".").replace(".py", "")
            full_module_path = f"dot_agent_kit.data.kits.{kit_name}.{module_path_str}"

            # Import the module
            try:
                module = importlib.import_module(full_module_path)
            except ImportError as e:
                raise click.ClickException(
                    f"Failed to import command '{command_def.name}' from kit '{manifest.name}': {e}"
                ) from e

            # Get the command function (convert hyphenated name to snake_case)
            function_name = command_def.name.replace("-", "_")
            if not hasattr(module, function_name):
                msg = (
                    f"Command '{command_def.name}' in kit '{manifest.name}' "
                    f"does not have expected function '{function_name}' "
                    f"in module {full_module_path}"
                )
                raise click.ClickException(msg)

            command_func = getattr(module, function_name)

            # Add the command to the kit's group
            kit_command_group.add_command(command_func)

        # Add the kit's group to the run group
        run_group.add_command(kit_command_group)


# Load all kit commands when module is imported
_load_kit_commands()
