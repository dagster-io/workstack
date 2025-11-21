"""Runs command implementation."""

import click

from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.core.context import ErkContext


@click.command("runs")
@click.pass_obj
def runs_cmd(ctx: ErkContext) -> None:
    """Show GitHub Actions workflow runs for plan implementations."""
    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)

    # Query workflow runs
    runs = ctx.github.list_workflow_runs(repo.root, "implement-plan.yml")

    # Group by branch (keep most recent per branch)
    branch_to_latest: dict[str, tuple[str, str, str | None]] = {}

    for run in runs:
        if run.branch not in branch_to_latest:
            branch_to_latest[run.branch] = (run.run_id, run.status, run.conclusion)

    # Handle empty state
    if not branch_to_latest:
        user_output("No workflow runs found for implement-plan.yml")
        return

    # Display results
    user_output("Plan Implementation Runs:\n")

    for branch, (run_id, status, conclusion) in branch_to_latest.items():
        # Format status indicator with color
        if status == "completed":
            if conclusion == "success":
                indicator = click.style("✓", fg="green")
                status_text = click.style("success", fg="green")
            elif conclusion == "failure":
                indicator = click.style("✗", fg="red")
                status_text = click.style("failure", fg="red")
            elif conclusion == "cancelled":
                indicator = click.style("⭕", fg="bright_black")
                status_text = click.style("cancelled", fg="bright_black")
            else:
                indicator = "?"
                status_text = conclusion or "unknown"
        elif status == "in_progress":
            indicator = click.style("⏳", fg="yellow")
            status_text = click.style("in_progress", fg="yellow")
        elif status == "queued":
            indicator = click.style("⏸", fg="bright_black")
            status_text = click.style("queued", fg="bright_black")
        else:
            indicator = "?"
            status_text = status

        # Format branch name
        branch_styled = click.style(branch, fg="yellow")

        # Format run ID
        run_id_styled = click.style(f"run: {run_id}", fg="white", dim=True)

        user_output(f"  {branch_styled}  {indicator} {status_text}  ({run_id_styled})")

    user_output()
    user_output("View details: gh run view {run_id} --web")
