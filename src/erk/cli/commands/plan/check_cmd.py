"""Command to check plan status and display details."""

import click
from erk_shared.output.output import user_output

from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir


@click.command("check")
@click.argument("identifier", type=str)
@click.pass_obj
def check_plan(ctx: ErkContext, identifier: str) -> None:
    """Check plan status by issue number or GitHub URL.

    Fetches plan details and comments to display current status.

    Args:
        identifier: Plan identifier (e.g., "42" or GitHub URL)
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    repo_root = repo.root

    # Parse identifier using Ensure pattern
    issue_number = Ensure.parse_github_issue_reference(identifier)

    # Fetch issue using Ensure pattern for GitHub API call
    issue = Ensure.github_api_call(
        lambda: ctx.issues.get_issue(repo_root, issue_number), error_context="Failed to fetch issue"
    )

    # Fetch comments using Ensure pattern for GitHub API call
    comments = Ensure.github_api_call(
        lambda: ctx.issues.get_issue_comments(repo_root, issue_number),
        error_context="Failed to fetch comments",
    )

    # Display plan details
    user_output("")
    user_output(click.style(issue.title, bold=True))
    user_output("")

    # Display state
    state_color = "green" if issue.state == "OPEN" else "red"
    user_output(f"State: {click.style(issue.state, fg=state_color)}")
    user_output(f"Issue: #{issue_number}")

    # Display comment count
    comment_count = len(comments)
    user_output(f"Comments: {comment_count}")
