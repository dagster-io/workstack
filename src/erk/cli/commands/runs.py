"""Runs command implementation."""

import click
from erk_shared.github.emoji import get_checks_status_emoji, get_issue_state_emoji
from erk_shared.output.output import user_output
from rich.console import Console
from rich.table import Table

from erk.cli.commands.plan.list_cmd import format_pr_cell, select_display_pr
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.display_utils import format_workflow_outcome, format_workflow_run_id


@click.group("runs", invoke_without_command=True)
@click.option("--show-legacy", is_flag=True, help="Show all runs including legacy runs.")
@click.pass_context
def runs_cmd(click_ctx: click.Context, show_legacy: bool) -> None:
    """View GitHub Actions workflow runs for plan implementations."""
    if click_ctx.invoked_subcommand is None:
        # Default behavior: show list view
        _list_runs(click_ctx, show_legacy)


def _extract_issue_number(display_title: str | None) -> int | None:
    """Extract issue number from display_title format '123:abc456'.

    Handles:
    - New format: "123:abc456" → 123
    - Old format: "Issue title [abc123]" → None (no colon at start)
    - None or empty → None
    """
    if not display_title or ":" not in display_title:
        return None
    parts = display_title.split(":", 1)
    # Validate that the first part is a number
    first_part = parts[0].strip()
    if not first_part.isdigit():
        return None
    return int(first_part)


def _list_runs(click_ctx: click.Context, show_all: bool = False) -> None:
    """List workflow runs in a run-centric table view."""
    ctx: ErkContext = click_ctx.obj

    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)

    # 1. Fetch workflow runs from dispatch-erk-queue.yml
    runs = ctx.github.list_workflow_runs(repo.root, "dispatch-erk-queue.yml")

    # Handle empty state
    if not runs:
        user_output("No workflow runs found")
        return

    # Filter out runs without plans unless --show-legacy flag is set
    if not show_all:
        runs = [run for run in runs if _extract_issue_number(run.display_title) is not None]
        if not runs:
            user_output("No runs with plans found. Use --show-legacy to see all runs.")
            return

    # 2. Extract issue numbers from display_title (format: "123:abc456")
    issue_numbers: list[int] = []
    for run in runs:
        issue_num = _extract_issue_number(run.display_title)
        if issue_num is not None:
            issue_numbers.append(issue_num)

    # 3. Fetch issues for titles (using issues interface)
    issues = ctx.issues.list_issues(repo.root, labels=["erk-plan"])
    issue_map = {issue.number: issue for issue in issues}

    # Second filtering pass - remove runs where we can't display title
    if not show_all:
        filtered_runs = []
        for run in runs:
            issue_num = _extract_issue_number(run.display_title)
            if issue_num is None:
                continue  # Already filtered, but defensive check

            # Filter if issue not found
            if issue_num not in issue_map:
                continue

            # Filter if title is empty
            issue = issue_map[issue_num]
            if not issue.title or not issue.title.strip():
                continue

            filtered_runs.append(run)

        runs = filtered_runs

        # Show message if ALL runs filtered
        if not runs:
            user_output("No runs with plans found. Use --show-legacy to see all runs.")
            return

    # 4. Batch fetch PRs linked to issues
    pr_linkages: dict[int, list] = {}
    if issue_numbers:
        pr_linkages = ctx.github.get_prs_linked_to_issues(repo.root, issue_numbers)

    # Determine use_graphite for URL selection
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False

    # 5. Build table
    table = Table(show_header=True, header_style="bold")
    table.add_column("run-id", style="cyan", no_wrap=True)
    table.add_column("status", no_wrap=True, width=14)
    table.add_column("plan", no_wrap=True)
    table.add_column("state", no_wrap=True, width=4)
    table.add_column("title", no_wrap=True)
    table.add_column("pr", no_wrap=True)
    table.add_column("chks", no_wrap=True)

    # Build repo URL for links
    # Extract owner/repo from issue URL if available, otherwise use git remote
    owner, repo_name = None, None
    if issues and issues[0].url:
        # Parse from URL like https://github.com/owner/repo/issues/123
        parts = issues[0].url.split("/")
        if len(parts) >= 5:
            owner = parts[-4]
            repo_name = parts[-3]

    for run in runs:
        issue_num = _extract_issue_number(run.display_title)

        # Format run-id with link
        workflow_url = None
        if owner and repo_name:
            workflow_url = f"https://github.com/{owner}/{repo_name}/actions/runs/{run.run_id}"
        run_id_cell = format_workflow_run_id(run, workflow_url)

        # Format status
        status_cell = format_workflow_outcome(run)

        # Handle legacy runs where we can't parse the issue number
        # Show "X" to indicate "can't parse" vs "-" for "no data"
        if issue_num is None:
            # Legacy format - can't extract issue linkage
            plan_cell = "[dim]X[/dim]"
            state_cell = "[dim]X[/dim]"
            title_cell = "[dim]X[/dim]"
            pr_cell = "[dim]X[/dim]"
            checks_cell = "[dim]X[/dim]"
        else:
            # New format - have issue number, try to get data
            issue_url = None
            if owner and repo_name:
                issue_url = f"https://github.com/{owner}/{repo_name}/issues/{issue_num}"
            # Make plan number clickable
            if issue_url:
                plan_cell = f"[link={issue_url}][cyan]#{issue_num}[/cyan][/link]"
            else:
                plan_cell = f"[cyan]#{issue_num}[/cyan]"

            # Get title and state from issue map
            if issue_num in issue_map:
                issue = issue_map[issue_num]

                # Get state emoji
                state_cell = get_issue_state_emoji(issue.state)

                title = issue.title
                # Truncate to 50 characters
                if len(title) > 50:
                    title = title[:47] + "..."
                title_cell = title
            else:
                state_cell = "[dim]-[/dim]"
                title_cell = "[dim]-[/dim]"

            # Format PR column
            pr_cell = "-"
            checks_cell = "-"
            if issue_num in pr_linkages:
                prs = pr_linkages[issue_num]
                selected_pr = select_display_pr(prs)
                if selected_pr is not None:
                    graphite_url = ctx.graphite.get_graphite_url(
                        selected_pr.owner, selected_pr.repo, selected_pr.number
                    )
                    pr_cell = format_pr_cell(
                        selected_pr, use_graphite=use_graphite, graphite_url=graphite_url
                    )
                    checks_cell = get_checks_status_emoji(selected_pr)

        table.add_row(
            run_id_cell,
            status_cell,
            plan_cell,
            state_cell,
            title_cell,
            pr_cell,
            checks_cell,
        )

    # Output table to stderr (consistent with user_output convention)
    console = Console(stderr=True, width=200, force_terminal=True)
    console.print(table)
    console.print()  # Add blank line after table


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
        current_branch = Ensure.not_none(
            ctx.git.get_current_branch(ctx.cwd), "Could not determine current branch"
        )

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
