"""Command to retry a queued plan."""

import subprocess
from datetime import UTC, datetime
from urllib.parse import urlparse

import click
from erk_shared.github.metadata import (
    PlanRetrySchema,
    create_metadata_block,
    parse_metadata_blocks,
    render_erk_issue_event,
)
from erk_shared.output.output import user_output

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir

ERK_PLAN_LABEL = "erk-plan"


@click.command("retry")
@click.argument("identifier", type=str)
@click.pass_obj
def retry_plan(ctx: ErkContext, identifier: str) -> None:
    """Retry a queued plan by re-triggering the GitHub Actions workflow.

    Triggers the dispatch-erk-queue workflow via direct dispatch again.
    Tracks retry count via metadata comments.

    Args:
        identifier: Plan identifier (e.g., "42" or GitHub URL)
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    repo_root = repo.root

    # Parse identifier to get issue number
    if identifier.isdigit():
        issue_number = int(identifier)
    else:
        # Parse GitHub URL
        parsed = urlparse(identifier)
        if parsed.hostname == "github.com" and parsed.path:
            parts = parsed.path.rstrip("/").split("/")
            if len(parts) >= 2 and parts[-2] == "issues":
                try:
                    issue_number = int(parts[-1])
                except ValueError as e:
                    user_output(click.style("Error: ", fg="red") + "Invalid issue number in URL")
                    raise SystemExit(1) from e
            else:
                user_output(click.style("Error: ", fg="red") + "Invalid GitHub issue URL")
                raise SystemExit(1)
        else:
            user_output(
                click.style("Error: ", fg="red")
                + "Invalid identifier. Use issue number or GitHub URL"
            )
            raise SystemExit(1)

    # Fetch issue from GitHub
    try:
        issue = ctx.issues.get_issue(repo_root, issue_number)
        ctx.feedback.info(f"Fetched issue #{issue_number}")
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from e

    # Validate issue state (LBYL pattern)
    if issue.state != "OPEN":
        user_output(click.style("Error: ", fg="red") + "Cannot retry closed plan")
        raise SystemExit(1)

    if ERK_PLAN_LABEL not in issue.labels:
        user_output(click.style("Error: ", fg="red") + "Issue is not an erk plan")
        raise SystemExit(1)

    # Calculate retry count by parsing all comments
    try:
        comments = ctx.issues.get_issue_comments(repo_root, issue_number)
        ctx.feedback.info(f"Parsing {len(comments)} comment(s) for retry history")
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from e

    # Parse all comments to find previous retry metadata
    previous_retry_count = 0
    previous_retry_timestamp = None

    for comment_body in comments:
        blocks = parse_metadata_blocks(comment_body)
        for block in blocks:
            if block.key == "plan-retry":
                retry_count = block.data.get("retry_count", 0)
                if retry_count > previous_retry_count:
                    previous_retry_count = retry_count
                    previous_retry_timestamp = block.data.get("retry_timestamp")

    new_retry_count = previous_retry_count + 1

    # Get GitHub username from gh CLI (requires authentication)
    try:
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True,
            check=True,
        )
        triggered_by = result.stdout.strip()
    except subprocess.CalledProcessError:
        triggered_by = "unknown"

    if not triggered_by:
        triggered_by = "unknown"

    # Trigger workflow via direct dispatch
    ctx.feedback.info("Triggering dispatch-erk-queue workflow...")
    try:
        ctx.github.trigger_workflow(
            repo_root=repo_root,
            workflow="dispatch-erk-queue.yml",
            inputs={"issue_number": str(issue_number)},
        )
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from e

    # Post metadata comment with retry information
    retry_timestamp = datetime.now(UTC).isoformat()
    metadata_data = {
        "retry_timestamp": retry_timestamp,
        "triggered_by": triggered_by,
        "retry_count": new_retry_count,
    }

    if previous_retry_timestamp is not None:
        metadata_data["previous_retry_timestamp"] = previous_retry_timestamp

    schema = PlanRetrySchema()
    metadata_block = create_metadata_block(
        key=schema.get_key(),
        data=metadata_data,
        schema=schema,
    )
    comment_body = render_erk_issue_event(
        title=f"🔄 Plan requeued (retry #{new_retry_count})",
        metadata=metadata_block,
    )

    try:
        ctx.issues.add_comment(repo_root, issue_number, comment_body)
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from e

    ctx.feedback.success(f"✓ Plan #{issue_number} requeued (retry #{new_retry_count})")
    ctx.feedback.success(f"View issue: {issue.url}")
