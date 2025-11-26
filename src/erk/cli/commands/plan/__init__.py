"""Plan command group."""

import click

from erk.cli.commands.plan.check_cmd import check_plan
from erk.cli.commands.plan.close_cmd import close_plan
from erk.cli.commands.plan.create_remote_cmd import create_remote_cmd
from erk.cli.commands.plan.get import get_plan
from erk.cli.commands.plan.log_cmd import plan_log
from erk.cli.commands.plan.retry_cmd import retry_plan


@click.group("plan")
def plan_group() -> None:
    """Manage implementation plans."""
    pass


plan_group.add_command(check_plan)
plan_group.add_command(close_plan)
plan_group.add_command(create_remote_cmd)
plan_group.add_command(get_plan)
plan_group.add_command(plan_log, name="log")
plan_group.add_command(retry_plan)
