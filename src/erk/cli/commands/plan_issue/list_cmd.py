"""Command to list plan issues with filtering."""

import click

from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.plan_issue_store import PlanIssueQuery, PlanIssueState
from erk.core.repo_discovery import ensure_repo_dir


@click.command("list")
@click.option(
    "--label",
    multiple=True,
    help="Filter by label (can be specified multiple times for AND logic)",
)
@click.option(
    "--state",
    type=click.Choice(["open", "closed"], case_sensitive=False),
    help="Filter by state",
)
@click.option(
    "--assignee",
    type=str,
    help="Filter by assignee username",
)
@click.option(
    "--limit",
    type=int,
    help="Maximum number of results to return",
)
@click.pass_obj
def list_plan_issues(
    ctx: ErkContext,
    label: tuple[str, ...],
    state: str | None,
    assignee: str | None,
    limit: int | None,
) -> None:
    """List plan issues with optional filters.

    Examples:
        erk plan-issue list
        erk plan-issue list --label erk-plan --state open
        erk plan-issue list --label erk-plan --label erk-queue
        erk plan-issue list --assignee alice --limit 10
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    repo_root = ensure_repo_dir(repo)

    # Build query from CLI options
    labels_list = list(label) if label else None
    state_enum = None
    if state:
        state_enum = PlanIssueState.OPEN if state.lower() == "open" else PlanIssueState.CLOSED

    query = PlanIssueQuery(
        labels=labels_list,
        state=state_enum,
        assignee=assignee,
        limit=limit,
    )

    try:
        plan_issues = ctx.plan_issue_store.list_plan_issues(repo_root, query)
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from e

    if not plan_issues:
        user_output("No plan issues found matching the criteria.")
        return

    # Display results
    user_output(f"\nFound {len(plan_issues)} plan issue(s):\n")

    for issue in plan_issues:
        # Format state with color
        state_color = "green" if issue.state == PlanIssueState.OPEN else "red"
        state_str = click.style(issue.state.value, fg=state_color)

        # Format identifier
        id_str = click.style(f"#{issue.plan_issue_identifier}", fg="cyan")

        # Format labels
        labels_str = ""
        if issue.labels:
            labels_str = " " + " ".join(
                click.style(f"[{label}]", fg="bright_magenta") for label in issue.labels
            )

        # Build line
        line = f"{id_str} ({state_str}){labels_str} {issue.title}"
        user_output(line)

    user_output("")
