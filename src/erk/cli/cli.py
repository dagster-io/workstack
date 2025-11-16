import click

from erk.cli.commands.completion import completion_group
from erk.cli.commands.config import config_group
from erk.cli.commands.consolidate import consolidate_cmd
from erk.cli.commands.create import create
from erk.cli.commands.current import current_cmd
from erk.cli.commands.down import down_cmd
from erk.cli.commands.gt import graphite_group
from erk.cli.commands.init import init_cmd
from erk.cli.commands.jump import jump_cmd
from erk.cli.commands.land_stack import land_stack
from erk.cli.commands.list import list_cmd, ls_cmd
from erk.cli.commands.move import move_cmd
from erk.cli.commands.prepare_cwd_recovery import prepare_cwd_recovery_cmd
from erk.cli.commands.remove import remove_cmd, rm_cmd
from erk.cli.commands.rename import rename_cmd
from erk.cli.commands.shell_integration import hidden_shell_cmd
from erk.cli.commands.split import split_cmd
from erk.cli.commands.status import status_cmd
from erk.cli.commands.switch import switch_cmd
from erk.cli.commands.sync import sync_cmd
from erk.cli.commands.tree import tree_cmd
from erk.cli.commands.up import up_cmd
from erk.core.context import create_context

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])  # terse help flags


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(package_name="erk")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Manage git worktrees in a global worktrees directory."""
    # Only create context if not already provided (e.g., by tests)
    if ctx.obj is None:
        ctx.obj = create_context(dry_run=False)


# Register all commands
cli.add_command(completion_group)
cli.add_command(consolidate_cmd)
cli.add_command(create)
cli.add_command(current_cmd)
cli.add_command(down_cmd)
cli.add_command(jump_cmd)
cli.add_command(land_stack)
cli.add_command(switch_cmd)
cli.add_command(up_cmd)
cli.add_command(list_cmd)
cli.add_command(ls_cmd)
cli.add_command(status_cmd)
cli.add_command(init_cmd)
cli.add_command(move_cmd)
cli.add_command(remove_cmd)
cli.add_command(rm_cmd)
cli.add_command(rename_cmd)
cli.add_command(config_group)
cli.add_command(split_cmd)
cli.add_command(sync_cmd)
cli.add_command(tree_cmd)
cli.add_command(graphite_group)
cli.add_command(hidden_shell_cmd)
cli.add_command(prepare_cwd_recovery_cmd)


def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()
