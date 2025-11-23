"""Plan issue commands for querying plan storage."""

import click

from erk.cli.commands.plan_issue.get import get_plan_issue
from erk.cli.commands.plan_issue.implement import implement_plan_issue
from erk.cli.commands.plan_issue.list_cmd import list_plan_issues, ls_plan_issues


@click.group("plan-issue")
def plan_issue_group() -> None:
    """Query plan issues from storage providers."""
    pass


# Register subcommands
plan_issue_group.add_command(get_plan_issue)
plan_issue_group.add_command(implement_plan_issue)
plan_issue_group.add_command(list_plan_issues)
plan_issue_group.add_command(ls_plan_issues)
