"""Runs command implementation."""

import json

import click

from erk.cli.core import discover_repo_context
from erk.cli.output import machine_output, user_output
from erk.core.context import ErkContext
from erk.core.github.types import WorkflowRun


def _workflow_run_to_json(run: WorkflowRun | None, *, error: str | None = None) -> str:
    """Convert WorkflowRun to JSON or return status object.

    Args:
        run: WorkflowRun object or None
        error: Optional error message for error state

    Returns:
        JSON string representing the run or status
    """
    if error:
        return json.dumps({"status": "error", "error": error})

    if run is None:
        return json.dumps({"status": "no_run"})

    return json.dumps({
        "run_id": run.run_id,
        "status": run.status,
        "conclusion": run.conclusion,
        "branch": run.branch,
        "head_sha": run.head_sha,
    })


@click.group("runs", invoke_without_command=True)
@click.pass_context
def runs_cmd(click_ctx: click.Context) -> None:
    """View GitHub Actions workflow runs for plan implementations."""
    if click_ctx.invoked_subcommand is None:
        # Default behavior: show list view
        _list_runs(click_ctx)


def _list_runs(click_ctx: click.Context) -> None:
    """List workflow runs (default behavior for runs command)."""
    ctx: ErkContext = click_ctx.obj

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


@runs_cmd.command()
@click.argument("run_id", required=False)
@click.pass_context
def logs(click_ctx: click.Context, run_id: str | None) -> None:
    """View logs for a workflow run.

    If RUN_ID is not provided, shows logs for the most recent run
    on the current branch.
    """
    ctx: ErkContext = click_ctx.obj

    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)

    if run_id is None:
        # Auto-detect: find most recent run for current branch
        current_branch = ctx.git.get_current_branch(ctx.cwd)
        if current_branch is None:
            user_output(click.style("Error: ", fg="red") + "Could not determine current branch")
            raise SystemExit(1)

        runs = ctx.github.list_workflow_runs(repo.root, "implement-plan.yml", limit=50)
        branch_runs = [r for r in runs if r.branch == current_branch]

        if not branch_runs:
            user_output(
                f"No workflow runs found for branch: {click.style(current_branch, fg='yellow')}"
            )
            raise SystemExit(1)

        # Most recent is first (list_workflow_runs returns newest first)
        run_id = branch_runs[0].run_id
        user_output(
            f"Showing logs for run {click.style(run_id, fg='cyan')} "
            f"on branch {click.style(current_branch, fg='yellow')}\n"
        )

    try:
        log_output = ctx.github.get_run_logs(repo.root, run_id)
        # Direct output - logs go to stdout for piping
        click.echo(log_output)
    except RuntimeError as e:
        click.echo(click.style("Error: ", fg="red") + str(e), err=True)
        raise SystemExit(1) from None


@runs_cmd.command()
@click.pass_context
def current(click_ctx: click.Context) -> None:
    """Get current branch's most recent workflow run as JSON.

    Returns JSON object with run information if found, or status marker if not.
    Suitable for use in scripting scenarios.
    """
    ctx: ErkContext = click_ctx.obj

    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)

    # Get current branch
    current_branch = ctx.git.get_current_branch(ctx.cwd)
    if current_branch is None:
        json_output = _workflow_run_to_json(None, error="Could not determine current branch")
        machine_output(json_output)
        raise SystemExit(1)

    # Query workflow runs
    runs = ctx.github.list_workflow_runs(repo.root, "implement-plan.yml", limit=50)

    # Filter by current branch
    branch_runs = [r for r in runs if r.branch == current_branch]

    # Return most recent run if found, otherwise no_run object
    if branch_runs:
        # Most recent is first (list_workflow_runs returns newest first)
        json_output = _workflow_run_to_json(branch_runs[0])
    else:
        json_output = _workflow_run_to_json(None)

    machine_output(json_output)
