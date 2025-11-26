"""Unified ls command that lists plans."""

import click

from erk.cli.commands.plan.list_cmd import _list_plans_impl
from erk.core.context import ErkContext


@click.command("ls")
@click.option(
    "--label",
    multiple=True,
    help="Filter by label",
)
@click.option(
    "--state",
    type=click.Choice(["open", "closed"], case_sensitive=False),
    help="Filter by state",
)
@click.option(
    "--action-state",
    type=click.Choice(["-", "pending", "running", "complete", "failed"], case_sensitive=False),
    help="Filter by action state",
)
@click.option(
    "--with-run",
    is_flag=True,
    help="Show workflow run columns (run-id, run-state)",
)
@click.option(
    "--limit",
    type=int,
    help="Maximum number of results to return",
)
@click.pass_obj
def ls_cmd(
    ctx: ErkContext,
    label: tuple[str, ...],
    state: str | None,
    action_state: str | None,
    with_run: bool,
    limit: int | None,
) -> None:
    """List plans.

    Examples:
        erk ls                           # List plans
        erk ls --label erk-plan          # List plans with label
        erk ls --with-run                # List plans with workflow run columns
    """
    _list_plans_impl(ctx, label, state, action_state, with_run, limit)
