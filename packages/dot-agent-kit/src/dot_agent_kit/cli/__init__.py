import click

from dot_agent_kit.cli.output import user_output
from dot_agent_kit.error_boundary import cli_error_boundary
from dot_agent_kit.version import __version__

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

# Track whether commands are registered
_commands_registered = False


class LazyGroup(click.Group):
    """Click Group that lazily loads commands."""

    def list_commands(self, ctx):
        """List available commands, registering them if needed."""
        global _commands_registered
        if not _commands_registered:
            _register_commands()
        return super().list_commands(ctx)

    def get_command(self, ctx, cmd_name):
        """Get a command by name, registering if needed."""
        global _commands_registered
        if not _commands_registered:
            _register_commands()
        return super().get_command(ctx, cmd_name)


@click.command(cls=LazyGroup, invoke_without_command=True, context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__)
@click.option("--debug", is_flag=True, help="Show full stack traces for errors")
@click.pass_context
def cli(ctx: click.Context, debug: bool) -> None:
    """Manage Claude Code kits."""
    # Initialize context object and store debug flag
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug

    if ctx.invoked_subcommand is None:
        user_output(ctx.get_help())


def _register_commands() -> None:
    """Register all commands with the CLI group."""
    global _commands_registered

    if _commands_registered:
        return

    from dot_agent_kit.commands import check
    from dot_agent_kit.commands.artifact import artifact_group
    from dot_agent_kit.commands.hook import hook_group
    from dot_agent_kit.commands.init import init
    from dot_agent_kit.commands.kit import kit_group
    from dot_agent_kit.commands.md import md_group
    from dot_agent_kit.commands.run import run_group
    from dot_agent_kit.commands.status import st, status

    cli.add_command(check.check)
    cli.add_command(init)
    cli.add_command(status)
    cli.add_command(st)

    # Register command groups
    cli.add_command(artifact_group)
    cli.add_command(hook_group)
    cli.add_command(kit_group)
    cli.add_command(md_group)
    cli.add_command(run_group)

    _commands_registered = True


def main() -> None:
    """Entry point with error boundary."""
    cli_error_boundary(cli)()


if __name__ == "__main__":
    main()
