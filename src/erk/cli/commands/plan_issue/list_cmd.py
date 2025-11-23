"""Command to list plan issues with filtering."""

from collections.abc import Callable

import click

from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.plan_issue_store import PlanIssueQuery, PlanIssueState
from erk.core.repo_discovery import ensure_erk_metadata_dir


def plan_issue_list_options[**P, T](f: Callable[P, T]) -> Callable[P, T]:
    """Shared options for list/ls commands."""
    f = click.option(
        "--label",
        multiple=True,
        help="Filter by label (can be specified multiple times for AND logic)",
    )(f)
    f = click.option(
        "--state",
        type=click.Choice(["open", "closed"], case_sensitive=False),
        help="Filter by state",
    )(f)
    f = click.option(
        "--limit",
        type=int,
        help="Maximum number of results to return",
    )(f)
    return f


def _list_plan_issues_impl(
    ctx: ErkContext,
    label: tuple[str, ...],
    state: str | None,
    limit: int | None,
) -> None:
    """Implementation logic for listing plan issues with optional filters."""
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)  # Ensure erk metadata directories exist
    repo_root = repo.root  # Use git repository root for GitHub operations

    # Build query from CLI options
    labels_list = list(label) if label else None
    state_enum = None
    if state:
        state_enum = PlanIssueState.OPEN if state.lower() == "open" else PlanIssueState.CLOSED

    query = PlanIssueQuery(
        labels=labels_list,
        state=state_enum,
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


@click.command("list")
@plan_issue_list_options
@click.pass_obj
def list_plan_issues(
    ctx: ErkContext,
    label: tuple[str, ...],
    state: str | None,
    limit: int | None,
) -> None:
    """List plan issues with optional filters.

    Examples:
        erk plan-issue list
        erk plan-issue list --label erk-plan --state open
        erk plan-issue list --label erk-plan --label erk-queue
        erk plan-issue list --limit 10
    """
    _list_plan_issues_impl(ctx, label, state, limit)


# Register ls as a hidden alias (won't show in help)
@click.command("ls", hidden=True)
@plan_issue_list_options
@click.pass_obj
def ls_plan_issues(
    ctx: ErkContext,
    label: tuple[str, ...],
    state: str | None,
    limit: int | None,
) -> None:
    """List plan issues with optional filters (alias of 'list')."""
    _list_plan_issues_impl(ctx, label, state, limit)
