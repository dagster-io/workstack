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
    "--run-state",
    type=click.Choice(
        ["queued", "in_progress", "success", "failure", "cancelled"],
        case_sensitive=False,
    ),
    help="Filter by workflow run state",
)
@click.option(
    "--runs",
    "-r",
    is_flag=True,
    default=False,
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
    run_state: str | None,
    runs: bool,
    limit: int | None,
) -> None:
    """List plans.

    Examples:
        erk ls                           # List plans
        erk ls --label erk-plan          # List plans with label
        erk ls --runs                    # List plans with workflow run columns
    """
    _list_plans_impl(ctx, label, state, run_state, runs, limit)
