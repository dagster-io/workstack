import click

from dot_agent_kit.commands import check
from dot_agent_kit.commands.artifact import artifact_group
from dot_agent_kit.commands.hook import hook_group
from dot_agent_kit.commands.init import init
from dot_agent_kit.commands.kit import kit_group
from dot_agent_kit.commands.status import st, status
from dot_agent_kit.error_boundary import cli_error_boundary
from dot_agent_kit.version import __version__

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(invoke_without_command=True, context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Manage Claude Code kits."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Register top-level commands
cli.add_command(check.check)
cli.add_command(init)
cli.add_command(status)
cli.add_command(st)

# Register command groups
cli.add_command(artifact_group)
cli.add_command(hook_group)
cli.add_command(kit_group)


def main() -> None:
    """Entry point with error boundary."""
    cli_error_boundary(cli)()


if __name__ == "__main__":
    main()
