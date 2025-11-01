import click

from dot_agent_kit import __version__
from dot_agent_kit.commands import (
    check,
    check_sync,
    hook,
    init,
    install,
    list,
    remove,
    search,
    status,
    sync,
    update,
)

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(invoke_without_command=True, context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Manage Claude Code kits."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


cli.add_command(init.init)
cli.add_command(install.install)
cli.add_command(check.check)
cli.add_command(check_sync.check_sync)
cli.add_command(sync.sync)
cli.add_command(update.update)
cli.add_command(remove.remove)
cli.add_command(status.status)
cli.add_command(search.search)
cli.add_command(list.list_cmd)
cli.add_command(list.ls_cmd)
cli.add_command(hook.hook)


if __name__ == "__main__":
    cli()
