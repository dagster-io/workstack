"""Command to fetch and display a single plan issue."""

import click

from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_repo_dir


@click.command("get")
@click.argument("identifier", type=str)
@click.pass_obj
def get_plan_issue(ctx: ErkContext, identifier: str) -> None:
    """Fetch and display a plan issue by identifier.

    Args:
        identifier: Plan issue identifier (e.g., "42" for GitHub)
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_repo_dir(repo)  # Ensure erk metadata directories exist
    repo_root = repo.root  # Use git repository root for GitHub operations

    try:
        plan_issue = ctx.plan_issue_store.get_plan_issue(repo_root, identifier)
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from e

    # Display plan issue details
    user_output("")
    user_output(click.style(plan_issue.title, bold=True))
    user_output("")

    # Display metadata
    state_color = "green" if plan_issue.state.value == "OPEN" else "red"
    user_output(
        f"State: {click.style(plan_issue.state.value, fg=state_color)} | "
        f"ID: {click.style(identifier, fg='cyan')}"
    )
    user_output(f"URL: {plan_issue.url}")

    # Display labels
    if plan_issue.labels:
        labels_str = ", ".join(
            click.style(f"[{label}]", fg="bright_magenta") for label in plan_issue.labels
        )
        user_output(f"Labels: {labels_str}")

    # Display assignees
    if plan_issue.assignees:
        assignees_str = ", ".join(plan_issue.assignees)
        user_output(f"Assignees: {assignees_str}")

    # Display timestamps
    created = plan_issue.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    updated = plan_issue.updated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    user_output(f"Created: {created}")
    user_output(f"Updated: {updated}")

    # Display body if present
    if plan_issue.body:
        user_output("")
        user_output(click.style("Description:", bold=True))
        user_output(plan_issue.body)
