"""Unified ls command that lists plans by default, worktrees with --worktrees flag."""

import click

from erk.cli.commands.plan.list_cmd import _list_plans_impl
from erk.cli.commands.wt.list_cmd import _list_worktrees
from erk.core.context import ErkContext


@click.command("ls")
@click.option("--worktrees", is_flag=True, help="List worktrees instead of plans")
@click.option(
    "--ci",
    is_flag=True,
    help="Fetch CI check status from GitHub (slower, worktrees only)",
)
@click.option(
    "--label",
    multiple=True,
    help="Filter by label (plans only)",
)
@click.option(
    "--state",
    type=click.Choice(["open", "closed"], case_sensitive=False),
    help="Filter by state (plans only)",
)
@click.option(
    "--action-state",
    type=click.Choice(["-", "pending", "running", "complete", "failed"], case_sensitive=False),
    help="Filter by action state (plans only)",
)
@click.option(
    "--with-run",
    is_flag=True,
    help="Show workflow run columns (run-id, run-state, plans only)",
)
@click.option(
    "--limit",
    type=int,
    help="Maximum number of results to return (plans only)",
)
@click.pass_obj
def ls_cmd(
    ctx: ErkContext,
    worktrees: bool,
    ci: bool,
    label: tuple[str, ...],
    state: str | None,
    action_state: str | None,
    with_run: bool,
    limit: int | None,
) -> None:
    """List plans (default) or worktrees.

    By default, lists plans. Use --worktrees to list worktrees instead.

    Examples:
        erk ls                           # List plans
        erk ls --worktrees               # List worktrees
        erk ls --label erk-plan          # List plans with label
        erk ls --worktrees --ci          # List worktrees with CI status
        erk ls --with-run                # List plans with workflow run columns
    """
    if worktrees:
        # List worktrees
        _list_worktrees(ctx, ci=ci)
    else:
        # List plans (default)
        _list_plans_impl(ctx, label, state, action_state, with_run, limit)
