import click

from dot_agent_kit import __version__
from dot_agent_kit.commands import status
from dot_agent_kit.commands.artifact import list as artifact_list
from dot_agent_kit.commands.hook import hook
from dot_agent_kit.commands.kit import check, install, list as kit_list, remove, sync, update

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(invoke_without_command=True, context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Manage Claude Code kits."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Root level commands
cli.add_command(status.status)


# Kit commands
@cli.group()
def kit() -> None:
    """Manage kits."""


kit.add_command(install.install)
kit.add_command(remove.remove)
kit.add_command(update.update)
kit.add_command(sync.sync)
kit.add_command(check.check)
kit.add_command(kit_list.list_kits, name="list")


# Artifact commands
@cli.group()
def artifact() -> None:
    """Manage artifacts."""


artifact.add_command(artifact_list.list_cmd, name="list")
artifact.add_command(artifact_list.ls_cmd, name="ls")


# Hook commands (already a group)
cli.add_command(hook)


if __name__ == "__main__":
    cli()
