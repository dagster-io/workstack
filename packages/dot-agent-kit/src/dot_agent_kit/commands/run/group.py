"""Run commands from bundled kits."""

import importlib
import traceback
from pathlib import Path
from typing import Any

import click

from dot_agent_kit.io import load_kit_manifest
from dot_agent_kit.models.kit import KitManifest
from dot_agent_kit.sources.bundled import BundledKitSource


@click.group()
@click.pass_context
def run_group(ctx: click.Context) -> None:
    """Run executable commands from bundled kits.

    Lists available kits with commands. Use 'dot-agent run <kit_id> --help'
    to see available commands for a specific kit.
    """


class LazyKitGroup(click.Group):
    """Click group that loads kit commands lazily on first access."""

    def __init__(
        self,
        kit_name: str,
        kit_dir: Path,
        manifest: KitManifest,
        debug: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize lazy kit group.

        Args:
            kit_name: Internal kit directory name
            kit_dir: Path to kit directory
            manifest: Kit manifest
            debug: Whether to show full tracebacks
            **kwargs: Additional arguments passed to click.Group
        """
        super().__init__(**kwargs)
        self._kit_name = kit_name
        self._kit_dir = kit_dir
        self._manifest = manifest
        self._debug = debug
        self._loaded = False

    def list_commands(self, ctx: click.Context) -> list[str]:
        """List available commands, loading them if needed."""
        if not self._loaded:
            self._load_commands(ctx)
        return super().list_commands(ctx)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """Get a command by name, loading commands if needed."""
        if not self._loaded:
            self._load_commands(ctx)
        return super().get_command(ctx, cmd_name)

    def _load_commands(self, ctx: click.Context) -> None:
        """Load all commands for this kit."""
        if self._loaded:
            return

        self._loaded = True

        # Get debug flag from context if available
        debug = self._debug
        if ctx.obj and "debug" in ctx.obj:
            debug = ctx.obj["debug"]

        for command_def in self._manifest.commands:
            # Validate command definition
            validation_errors = command_def.validate()
            if validation_errors:
                kit_name = self._manifest.name
                cmd_name = command_def.name
                error_msg = f"Invalid command '{cmd_name}' in kit '{kit_name}':\n"
                for error in validation_errors:
                    error_msg += f"  - {error}\n"
                click.echo(error_msg, err=True)
                if debug:
                    raise click.ClickException(error_msg)
                continue

            # Check that command file exists
            command_file = self._kit_dir / command_def.path
            if not command_file.exists():
                error_msg = (
                    f"Warning: Command file not found for '{command_def.name}' "
                    f"in kit '{self._manifest.name}': {command_file}\n"
                )
                click.echo(error_msg, err=True)
                if debug:
                    raise click.ClickException(error_msg)
                continue

            # Convert path to module path using pathlib
            command_path = Path(command_def.path)
            module_parts = command_path.with_suffix("").parts
            module_path_str = ".".join(module_parts)
            full_module_path = f"dot_agent_kit.data.kits.{self._kit_name}.{module_path_str}"

            # Import the module
            try:
                module = importlib.import_module(full_module_path)
            except ImportError as e:
                error_msg = (
                    f"Warning: Failed to import command '{command_def.name}' "
                    f"from kit '{self._manifest.name}': {e}\n"
                )
                click.echo(error_msg, err=True)
                if debug:
                    click.echo(traceback.format_exc(), err=True)
                continue

            # Get the command function (convert hyphenated name to snake_case)
            function_name = command_def.name.replace("-", "_")
            if not hasattr(module, function_name):
                error_msg = (
                    f"Warning: Command '{command_def.name}' in kit '{self._manifest.name}' "
                    f"does not have expected function '{function_name}' "
                    f"in module {full_module_path}\n"
                )
                click.echo(error_msg, err=True)
                if debug:
                    raise click.ClickException(error_msg)
                continue

            command_func = getattr(module, function_name)

            # Add the command to the kit's group
            self.add_command(command_func)


def _load_single_kit_commands(
    kit_name: str, kit_dir: Path, manifest: KitManifest, debug: bool = False
) -> click.Group | None:
    """Load commands for a single kit with error isolation.

    Args:
        kit_name: Internal kit directory name
        kit_dir: Path to kit directory
        manifest: Kit manifest
        debug: Whether to show full tracebacks

    Returns:
        Click group for kit, or None if kit failed to load
    """
    try:
        # Skip kits without commands
        if not manifest.commands:
            click.echo(f"Warning: Kit '{manifest.name}' has no commands, skipping\n", err=True)
            return None

        # Validate kit directory exists
        if not kit_dir.exists():
            error_msg = f"Warning: Kit directory not found: {kit_dir}\n"
            click.echo(error_msg, err=True)
            if debug:
                raise click.ClickException(error_msg)
            return None

        # Create lazy loading group for this kit
        kit_group = LazyKitGroup(
            kit_name=kit_name,
            kit_dir=kit_dir,
            manifest=manifest,
            debug=debug,
            name=manifest.name,
            help=manifest.description,
        )

        return kit_group

    except Exception as e:
        error_msg = f"Warning: Failed to load kit '{manifest.name}': {e}\n"
        click.echo(error_msg, err=True)
        if debug:
            click.echo(traceback.format_exc(), err=True)
            raise
        return None


def _load_kit_commands() -> None:
    """Dynamically load commands from all kits with commands."""
    source = BundledKitSource()
    available_kits = source.list_available()

    # Get the kits data directory
    data_dir = Path(__file__).parent.parent.parent / "data" / "kits"

    # Check data directory exists
    if not data_dir.exists():
        click.echo(f"Warning: Kits data directory not found: {data_dir}\n", err=True)
        return

    for kit_name in available_kits:
        kit_dir = data_dir / kit_name
        manifest_path = kit_dir / "kit.yaml"

        if not manifest_path.exists():
            continue

        manifest = load_kit_manifest(manifest_path)

        # Load kit commands with error isolation
        kit_group = _load_single_kit_commands(
            kit_name=kit_name, kit_dir=kit_dir, manifest=manifest, debug=False
        )

        # Skip if kit failed to load or has no commands
        if kit_group is None:
            continue

        # Add the kit's group to the run group
        run_group.add_command(kit_group)


# Load all kit commands when module is imported
_load_kit_commands()
