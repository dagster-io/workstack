"""Plan commands for querying plan storage."""

import click

from erk.cli.commands.plan.close_cmd import close_plan
from erk.cli.commands.plan.get import get_plan
from erk.cli.commands.plan.list_cmd import list_plans, ls_plans


@click.group("plan")
def plan_group() -> None:
    """Query plans from storage providers."""
    pass


# Register subcommands
plan_group.add_command(close_plan)
plan_group.add_command(get_plan)
plan_group.add_command(list_plans)
plan_group.add_command(ls_plans)
