"""Command to list plan issues with filtering."""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import click
from erk_shared.github.issues import GitHubIssues

from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.plan_issue_store import PlanIssueQuery, PlanIssueState
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.integrations.github.metadata_blocks import parse_metadata_blocks


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

    # Batch fetch all issue comments for worktree status
    issue_numbers: list[int] = []
    for issue in plan_issues:
        num = issue.metadata.get("number")
        if isinstance(num, int):
            issue_numbers.append(num)

    all_comments: dict[int, list[str]] = {}
    if issue_numbers:
        try:
            all_comments = ctx.issues.get_multiple_issue_comments(repo_root, issue_numbers)
        except Exception:
            # If batch fetch fails, continue without worktree status
            pass

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

        # Query worktree status from batch-fetched comments
        worktree_str = ""
        issue_number = issue.metadata.get("number")
        if isinstance(issue_number, int) and issue_number in all_comments:
            comments = all_comments[issue_number]
            # Parse worktree metadata from comments
            worktree_name = _parse_worktree_from_comments(comments)
            if worktree_name:
                worktree_str = f" {click.style(worktree_name, fg='yellow')}"

        # Build line
        line = f"{id_str} ({state_str}){labels_str} {issue.title}{worktree_str}"
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
