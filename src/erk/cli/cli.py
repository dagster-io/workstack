import click

from erk.cli.commands.admin import admin_group
from erk.cli.commands.checkout import checkout_cmd
from erk.cli.commands.completion import completion_group
from erk.cli.commands.config import config_group
from erk.cli.commands.down import down_cmd
from erk.cli.commands.implement import implement
from erk.cli.commands.init import init_cmd
from erk.cli.commands.ls import ls_cmd
from erk.cli.commands.plan.close_cmd import close_plan
from erk.cli.commands.plan.get import get_plan
from erk.cli.commands.plan.list_cmd import list_plans
from erk.cli.commands.plan.log_cmd import plan_log
from erk.cli.commands.plan.retry_cmd import retry_plan
from erk.cli.commands.pr import pr_group
from erk.cli.commands.prepare_cwd_recovery import prepare_cwd_recovery_cmd
from erk.cli.commands.runs import runs_cmd
from erk.cli.commands.shell_integration import hidden_shell_cmd
from erk.cli.commands.stack import stack_group
from erk.cli.commands.status import status_cmd
from erk.cli.commands.submit import submit_cmd
from erk.cli.commands.up import up_cmd
from erk.cli.commands.wt import wt_group
from erk.cli.help_formatter import GroupedCommandGroup
from erk.core.context import create_context

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])  # terse help flags


@click.group(cls=GroupedCommandGroup, context_settings=CONTEXT_SETTINGS)
@click.version_option(package_name="erk")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Manage git worktrees in a global worktrees directory."""
    # Only create context if not already provided (e.g., by tests)
    if ctx.obj is None:
        ctx.obj = create_context(dry_run=False)


# Register all commands
cli.add_command(admin_group)
cli.add_command(checkout_cmd)
cli.add_command(checkout_cmd, name="co")  # Alias
cli.add_command(close_plan, name="close")  # Plan command
cli.add_command(completion_group)
cli.add_command(config_group)
cli.add_command(down_cmd)
cli.add_command(get_plan, name="get")  # Plan command
cli.add_command(implement)
cli.add_command(init_cmd)
cli.add_command(list_plans, name="list")  # Plan command
cli.add_command(plan_log, name="log")  # Plan command
cli.add_command(ls_cmd)  # List plans
cli.add_command(pr_group)
cli.add_command(retry_plan, name="retry")  # Plan command
cli.add_command(runs_cmd)
cli.add_command(stack_group)
cli.add_command(status_cmd)
cli.add_command(submit_cmd)
cli.add_command(up_cmd)
cli.add_command(wt_group)
cli.add_command(hidden_shell_cmd)
cli.add_command(prepare_cwd_recovery_cmd)


def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()
