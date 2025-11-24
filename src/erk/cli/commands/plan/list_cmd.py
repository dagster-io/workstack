"""Command to list plans with filtering."""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import click
from erk_shared.github.emoji import get_checks_status_emoji, get_pr_status_emoji
from erk_shared.github.issues import GitHubIssues
from erk_shared.github.types import PullRequestInfo
from erk_shared.impl_folder import read_issue_reference
from rich.console import Console
from rich.table import Table

from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.plan_store import Plan, PlanQuery, PlanState
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.integrations.github.metadata_blocks import parse_metadata_blocks


def select_display_pr(prs: list[PullRequestInfo]) -> PullRequestInfo | None:
    """Select PR to display: prefer open, then merged, then closed.

    Args:
        prs: List of PRs sorted by created_at descending (most recent first)

    Returns:
        PR to display, or None if no PRs
    """
    # Check for open PRs (published or draft)
    open_prs = [pr for pr in prs if pr.state in ("OPEN", "DRAFT")]
    if open_prs:
        return open_prs[0]  # Most recent open

    # Fallback to merged PRs
    merged_prs = [pr for pr in prs if pr.state == "MERGED"]
    if merged_prs:
        return merged_prs[0]  # Most recent merged

    # Fallback to closed PRs
    closed_prs = [pr for pr in prs if pr.state == "CLOSED"]
    if closed_prs:
        return closed_prs[0]  # Most recent closed

    return None


def format_pr_cell(pr: PullRequestInfo, *, use_graphite: bool, graphite_url: str | None) -> str:
    """Format PR cell with clickable link and emoji: #123 👀 or #123 👀💥

    Args:
        pr: PR information
        use_graphite: If True, use Graphite URL; if False, use GitHub URL
        graphite_url: Graphite URL for the PR (None if unavailable)

    Returns:
        Formatted string for table cell with OSC 8 hyperlink
    """
    emoji = get_pr_status_emoji(pr)
    pr_text = f"#{pr.number}"

    # Determine which URL to use
    url = graphite_url if use_graphite else pr.url

    # Make PR number clickable if URL is available
    # Rich supports OSC 8 via [link=...] markup
    if url:
        return f"[link={url}]{pr_text}[/link] {emoji}"
    else:
        return f"{pr_text} {emoji}"


def format_checks_cell(pr: PullRequestInfo | None) -> str:
    """Format checks cell: ✅/🚫/🔄/-

    Args:
        pr: PR information, or None if no PR

    Returns:
        Formatted string for table cell
    """
    return get_checks_status_emoji(pr)


def determine_action_state(plan: Plan, all_comments: dict[int, list[str]]) -> str:
    """Determine simplified action state from plan metadata.

    Returns one of: "-", "Pending", "Running", "Complete", "Failed"

    Args:
        plan: The plan to determine state for
        all_comments: Dict mapping issue numbers to list of comment bodies

    Returns:
        Action state string for display
    """
    # Check if plan has erk-queue label
    if "erk-queue" not in plan.labels:
        return "-"

    # Get issue number from metadata
    issue_number = plan.metadata.get("number")
    if not isinstance(issue_number, int):
        return "-"

    # Get comments for this issue
    if issue_number not in all_comments:
        # Has label but no comments yet - pending
        return "Pending"

    comments = all_comments[issue_number]

    # Parse all metadata blocks from all comments
    # Track most recent by metadata key
    latest_blocks: dict[str, tuple[datetime, dict[str, object]]] = {}

    for comment_body in comments:
        blocks = parse_metadata_blocks(comment_body)
        for block in blocks:
            # Extract timestamp if present
            timestamp_str = block.data.get("timestamp")
            if timestamp_str and isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                # Use fallback timestamp if not present
                timestamp = datetime.min

            # Update if this is the most recent block for this key
            if block.key not in latest_blocks or timestamp > latest_blocks[block.key][0]:
                latest_blocks[block.key] = (timestamp, block.data)

    # Check for metadata in priority order
    # 1. erk-implementation-status - check status field
    if "erk-implementation-status" in latest_blocks:
        status = latest_blocks["erk-implementation-status"][1].get("status")
        if status == "complete":
            return "Complete"
        if status == "failed":
            return "Failed"
        if status in ("pending", "starting", "in_progress"):
            return "Running"

    # 2. workflow-started - means workflow is running
    if "workflow-started" in latest_blocks:
        return "Running"

    # 3. submission-queued - means queued but not started
    if "submission-queued" in latest_blocks:
        return "Pending"

    # Has erk-queue label but no metadata yet
    return "Pending"


def plan_list_options[**P, T](f: Callable[P, T]) -> Callable[P, T]:
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
        "--action-state",
        type=click.Choice(["-", "pending", "running", "complete", "failed"], case_sensitive=False),
        help="Filter by action state",
    )(f)
    f = click.option(
        "--limit",
        type=int,
        help="Maximum number of results to return",
    )(f)
    return f


def _parse_worktree_from_comments(comments: list[str]) -> str | None:
    """Parse worktree name from issue comments.

    Returns worktree name if exists, None otherwise.
    For multiple worktrees, returns most recent by timestamp.

    Args:
        comments: List of comment bodies (markdown strings)

    Returns:
        Worktree name if found, None otherwise
    """
    # Track all worktree metadata blocks with timestamps
    worktree_blocks: list[tuple[datetime, str]] = []

    # Search through comments for worktree metadata
    for comment_body in comments:
        blocks = parse_metadata_blocks(comment_body)
        for block in blocks:
            if block.key == "erk-worktree-creation":
                # Extract timestamp and worktree name
                timestamp_str = block.data.get("timestamp")
                worktree_name = block.data.get("worktree_name")

                if timestamp_str and worktree_name:
                    # Parse ISO 8601 timestamp
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    worktree_blocks.append((timestamp, worktree_name))

    # If no worktree blocks found, return None
    if not worktree_blocks:
        return None

    # Sort by timestamp descending and return most recent worktree name
    worktree_blocks.sort(reverse=True, key=lambda x: x[0])
    return worktree_blocks[0][1]


def get_worktree_status(
    github_issues: GitHubIssues,
    repo_root: Path,
    issue_number: int,
) -> str | None:
    """Query worktree status for an issue.

    Note: This function is deprecated in favor of batch fetching.
    Use get_multiple_issue_comments() for better performance.

    Returns worktree name if exists, None otherwise.
    For multiple worktrees, returns most recent by timestamp.

    Args:
        github_issues: GitHub issues integration instance
        repo_root: Repository root directory
        issue_number: Issue number to query

    Returns:
        Worktree name if found, None otherwise
    """
    # Get all comments for the issue
    comments = github_issues.get_issue_comments(repo_root, issue_number)
    return _parse_worktree_from_comments(comments)


def _list_plans_impl(
    ctx: ErkContext,
    label: tuple[str, ...],
    state: str | None,
    action_state: str | None,
    limit: int | None,
) -> None:
    """Implementation logic for listing plans with optional filters."""
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)  # Ensure erk metadata directories exist
    repo_root = repo.root  # Use git repository root for GitHub operations

    # Build query from CLI options
    labels_list = list(label) if label else None
    state_enum = None
    if state:
        state_enum = PlanState.OPEN if state.lower() == "open" else PlanState.CLOSED

    query = PlanQuery(
        labels=labels_list,
        state=state_enum,
        limit=limit,
    )

    try:
        plans = ctx.plan_store.list_plans(repo_root, query)
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from e

    if not plans:
        user_output("No plans found matching the criteria.")
        return

    # Display results header
    user_output(f"\nFound {len(plans)} plan(s):\n")

    # Batch fetch all issue comments for worktree status
    issue_numbers: list[int] = []
    for plan in plans:
        num = plan.metadata.get("number")
        if isinstance(num, int):
            issue_numbers.append(num)

    all_comments: dict[int, list[str]] = {}
    if issue_numbers:
        try:
            all_comments = ctx.issues.get_multiple_issue_comments(repo_root, issue_numbers)
        except Exception:
            # If batch fetch fails, continue without worktree status
            pass

    # Batch fetch PR linkages for all issues
    pr_linkages: dict[int, list[PullRequestInfo]] = {}
    if issue_numbers:
        try:
            pr_linkages = ctx.github.get_prs_linked_to_issues(repo_root, issue_numbers)
        except Exception:
            # If batch fetch fails, continue without PR info
            pass

    # Apply action state filter if specified
    if action_state:
        # Normalize action_state for comparison (user input is lowercase from click.Choice)
        normalized_filter = action_state.capitalize() if action_state != "-" else "-"
        filtered_plans: list[Plan] = []
        for plan in plans:
            plan_action_state = determine_action_state(plan, all_comments)
            if plan_action_state == normalized_filter:
                filtered_plans.append(plan)
        plans = filtered_plans

        # Check if filtering resulted in no plans
        if not plans:
            user_output("No plans found matching the criteria.")
            return

    # Build local worktree mapping from .impl/issue.json files
    worktree_by_issue: dict[int, str] = {}
    worktrees = ctx.git.list_worktrees(repo_root)
    for worktree in worktrees:
        impl_folder = worktree.path / ".impl"
        if impl_folder.exists() and impl_folder.is_dir():
            issue_ref = read_issue_reference(impl_folder)
            if issue_ref is not None:
                # If multiple worktrees have same issue, keep first found
                if issue_ref.issue_number not in worktree_by_issue:
                    worktree_by_issue[issue_ref.issue_number] = worktree.path.name

    # Determine use_graphite for URL selection
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False

    # Create Rich table with columns
    table = Table(show_header=True, header_style="bold")
    table.add_column("Plan", style="cyan", no_wrap=True)
    table.add_column("PR", no_wrap=True)
    table.add_column("Checks", no_wrap=True)
    table.add_column("State", no_wrap=True)
    table.add_column("Action", no_wrap=True, width=12)
    table.add_column("Title", no_wrap=True)
    table.add_column("Local Worktree", style="yellow", no_wrap=True)

    # Populate table rows
    for plan in plans:
        # Format issue number with clickable OSC 8 hyperlink
        id_text = f"#{plan.plan_identifier}"
        colored_id = f"[cyan]{id_text}[/cyan]"

        # Make ID clickable using OSC 8 if URL is available
        if plan.url:
            # Rich library supports OSC 8 via markup syntax
            issue_id = f"[link={plan.url}]{colored_id}[/link]"
        else:
            issue_id = colored_id

        # Format state with color
        state_color = "green" if plan.state == PlanState.OPEN else "red"
        state_str = f"[{state_color}]{plan.state.value}[/{state_color}]"

        # Determine action state with color coding
        action_state = determine_action_state(plan, all_comments)
        # Apply color styling based on state
        if action_state == "-":
            action_str = f"[dim]{action_state}[/dim]"
        elif action_state == "Pending":
            action_str = f"[yellow]{action_state}[/yellow]"
        elif action_state == "Running":
            action_str = f"[blue]{action_state}[/blue]"
        elif action_state == "Complete":
            action_str = f"[green]{action_state}[/green]"
        elif action_state == "Failed":
            action_str = f"[red]{action_state}[/red]"
        else:
            action_str = action_state

        # Truncate title to 50 characters with ellipsis
        title = plan.title
        if len(title) > 50:
            title = title[:47] + "..."

        # Query worktree status - check local .impl/issue.json first, then GitHub comments
        issue_number = plan.metadata.get("number")
        worktree_name = ""

        # Check local mapping first
        if isinstance(issue_number, int) and issue_number in worktree_by_issue:
            worktree_name = worktree_by_issue[issue_number]
        # Fall back to GitHub comments if not found locally
        elif isinstance(issue_number, int) and issue_number in all_comments:
            comments = all_comments[issue_number]
            # Parse worktree metadata from comments
            parsed_name = _parse_worktree_from_comments(comments)
            if parsed_name:
                worktree_name = parsed_name

        # Get PR info for this issue
        pr_cell = "-"
        checks_cell = "-"
        if isinstance(issue_number, int) and issue_number in pr_linkages:
            prs = pr_linkages[issue_number]
            selected_pr = select_display_pr(prs)
            if selected_pr is not None:
                graphite_url = ctx.graphite.get_graphite_url(
                    selected_pr.owner, selected_pr.repo, selected_pr.number
                )
                pr_cell = format_pr_cell(selected_pr, use_graphite=use_graphite, graphite_url=graphite_url)
                checks_cell = format_checks_cell(selected_pr)

        # Add row to table
        table.add_row(issue_id, pr_cell, checks_cell, state_str, action_str, title, worktree_name)

    # Output table to stderr (consistent with user_output convention)
    # Use width=200 to ensure proper display without truncation
    console = Console(stderr=True, width=200)
    console.print(table)
    console.print()  # Add blank line after table


@click.command("list")
@plan_list_options
@click.pass_obj
def list_plans(
    ctx: ErkContext,
    label: tuple[str, ...],
    state: str | None,
    action_state: str | None,
    limit: int | None,
) -> None:
    """List plans with optional filters.

    Examples:
        erk plan list
        erk plan list --label erk-plan --state open
        erk plan list --label erk-plan --label erk-queue
        erk plan list --limit 10
        erk plan list --action-state running
        erk plan list --action-state complete --state open
    """
    _list_plans_impl(ctx, label, state, action_state, limit)


# Register ls as a hidden alias (won't show in help)
@click.command("ls", hidden=True)
@plan_list_options
@click.pass_obj
def ls_plans(
    ctx: ErkContext,
    label: tuple[str, ...],
    state: str | None,
    action_state: str | None,
    limit: int | None,
) -> None:
    """List plans with optional filters (alias of 'list')."""
    _list_plans_impl(ctx, label, state, action_state, limit)
