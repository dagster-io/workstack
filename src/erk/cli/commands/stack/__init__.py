"""Stack operation commands for managing Graphite stacks."""

import click

from erk.cli.commands.stack.consolidate_cmd import consolidate_stack
from erk.cli.commands.stack.land_cmd import land_stack_cmd
from erk.cli.commands.stack.move_cmd import move_stack
from erk.cli.commands.stack.split_cmd import split_stack


@click.group("stack")
def stack_group() -> None:
    """Manage Graphite stack operations."""
    pass


# Register subcommands
stack_group.add_command(consolidate_stack, name="consolidate")
stack_group.add_command(land_stack_cmd, name="land")
stack_group.add_command(move_stack, name="move")
stack_group.add_command(split_stack, name="split")
