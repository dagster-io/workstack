import click

from dot_agent_kit import __version__
from dot_agent_kit.commands import status
from dot_agent_kit.commands.artifact import check, check_sync, list
from dot_agent_kit.commands.kit import init, install, remove, search, sync, update

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(invoke_without_command=True, context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Manage Claude Code kits."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.group()
def kit() -> None:
    """Manage kits and installations."""
    pass


@cli.group()
def artifact() -> None:
    """Manage artifacts."""
    pass


# Register top-level commands
cli.add_command(status.status)

# Register kit commands
kit.add_command(init.init)
kit.add_command(install.install)
kit.add_command(remove.remove)
kit.add_command(update.update)
kit.add_command(sync.sync)
kit.add_command(search.search)

# Register artifact commands
artifact.add_command(list.list_cmd)
artifact.add_command(list.ls_cmd)
artifact.add_command(check.check)
artifact.add_command(check_sync.check_sync)


if __name__ == "__main__":
    cli()
