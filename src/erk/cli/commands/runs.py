"""Runs command implementation."""

import click
from erk_shared.impl_folder import read_issue_reference
from rich.console import Console
from rich.table import Table

from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.core.context import ErkContext


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

    # Get repository owner/name for URL construction
    repo_info = ctx.github.get_repo_info(repo.root)
    if repo_info is None:
        # Fallback to simple display if repo info unavailable
        user_output("Plan Implementation Runs:\n")
        for branch in sorted(branch_to_latest.keys()):
            run_id, status, conclusion = branch_to_latest[branch]
            user_output(f"  {branch}: run {run_id} - {status}")
        return

    owner, repo_name = repo_info

    # Build worktree-to-issue mapping for Plan column
    worktree_by_branch: dict[str, int] = {}
    worktrees = ctx.git.list_worktrees(repo.root)
    for wt in worktrees:
        if wt.branch is None:
            continue
        impl_folder = wt.path / ".impl"
        if impl_folder.exists():
            issue_ref = read_issue_reference(impl_folder)
            if issue_ref:
                worktree_by_branch[wt.branch] = issue_ref.issue_number

    # Create Rich table
    console = Console()
    table = Table(title="Plan Implementation Runs")
    table.add_column("Branch", style="yellow")
    table.add_column("Status")
    table.add_column("Run", style="cyan")
    table.add_column("PR", style="cyan")
    table.add_column("Plan", style="cyan")

    # Add rows in alphabetical order by branch
    for branch in sorted(branch_to_latest.keys()):
        run_id, status, conclusion = branch_to_latest[branch]

        # Format status column
        if status == "completed":
            if conclusion == "success":
                status_cell = "[green]✓ pass[/green]"
            elif conclusion == "failure":
                status_cell = "[red]✗ fail[/red]"
            elif conclusion == "cancelled":
                status_cell = "[dim]⭕ cancelled[/dim]"
            else:
                status_cell = f"? {conclusion or 'unknown'}"
        elif status == "in_progress":
            status_cell = "[yellow]⏳ running[/yellow]"
        elif status == "queued":
            status_cell = "[dim]⏸ queued[/dim]"
        else:
            status_cell = f"? {status}"

        # Format Run column with clickable link
        run_url = f"https://github.com/{owner}/{repo_name}/actions/runs/{run_id}"
        run_cell = f"[link={run_url}]{run_id}[/link]"

        # Look up PR for this branch
        pr_info = ctx.github.get_pr_status(repo.root, branch, debug=False)
        if pr_info.pr_number:
            pr_url = f"https://github.com/{owner}/{repo_name}/pull/{pr_info.pr_number}"
            pr_cell = f"[link={pr_url}]#{pr_info.pr_number}[/link]"
        else:
            pr_cell = "-"

        # Look up Plan from local worktree
        plan_number = worktree_by_branch.get(branch)
        if plan_number:
            plan_url = f"https://github.com/{owner}/{repo_name}/issues/{plan_number}"
            plan_cell = f"[link={plan_url}]#{plan_number}[/link]"
        else:
            plan_cell = "-"

        table.add_row(branch, status_cell, run_cell, pr_cell, plan_cell)

    # Display table
    console.print(table)


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
