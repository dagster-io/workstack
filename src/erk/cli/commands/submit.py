"""Submit issue for remote AI implementation via GitHub Actions."""

import subprocess
from datetime import UTC, datetime

import click
from erk_shared.github.metadata import create_submission_queued_block, render_erk_issue_event

from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext

# Label used to queue issues for automated implementation
ERK_QUEUE_LABEL = "erk-queue"
ERK_PLAN_LABEL = "erk-plan"


@click.command("submit")
@click.argument("issue_number", type=int)
@click.pass_obj
def submit_cmd(ctx: ErkContext, issue_number: int) -> None:
    """Submit issue for remote AI implementation via GitHub Actions.

    Adds the erk-queue label to the specified GitHub issue, which triggers
    the dispatch-erk-queue.yml GitHub Actions workflow for automated implementation.

    The workflow will:
    - Create a branch from the trunk branch
    - Create .erp/ folder with plan content
    - Create a draft PR
    - Run the implementation

    Arguments:
        ISSUE_NUMBER: GitHub issue number to submit for implementation

    Requires:
        - Issue must have erk-plan label
        - Issue must be OPEN
        - Issue must not already have erk-queue label
    """
    # Get repository context
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        repo = discover_repo_context(ctx, ctx.cwd)

    # Fetch issue from GitHub
    try:
        issue = ctx.issues.get_issue(repo.root, issue_number)
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from None

    # Validate: must have erk-plan label
    if ERK_PLAN_LABEL not in issue.labels:
        user_output(
            click.style("Error: ", fg="red")
            + f"Issue #{issue_number} does not have {ERK_PLAN_LABEL} label\n\n"
            "Cannot submit non-plan issues for automated implementation.\n"
            "To create a plan, use: erk plan save"
        )
        raise SystemExit(1)

    # Validate: must be OPEN
    if issue.state != "OPEN":
        user_output(
            click.style("Error: ", fg="red") + f"Issue #{issue_number} is {issue.state}\n\n"
            "Cannot submit closed issues for automated implementation."
        )
        raise SystemExit(1)

    # Validate: must not already have erk-queue label
    if ERK_QUEUE_LABEL in issue.labels:
        user_output(
            click.style("Error: ", fg="red")
            + f"Issue #{issue_number} already has {ERK_QUEUE_LABEL} label\n\n"
            "This issue has already been submitted for automated implementation.\n"
            f"View issue: {issue.url}"
        )
        raise SystemExit(1)

    # Display issue details
    user_output("Submitting issue for automated implementation:")
    user_output(f"  Number: {click.style(f'#{issue_number}', fg='cyan')}")
    user_output(f"  Title:  {click.style(issue.title, fg='yellow')}")
    user_output(f"  State:  {click.style(issue.state, fg='green')}")
    user_output("")

    # Add erk-queue label to trigger workflow
    user_output(f"Adding {ERK_QUEUE_LABEL} label...")
    ctx.issues.ensure_label_on_issue(repo.root, issue_number, ERK_QUEUE_LABEL)

    # Trigger workflow via workflow_dispatch API
    user_output("Triggering GitHub Actions workflow...")
    try:
        # Get trunk branch
        trunk_branch = ctx.trunk_branch
        if trunk_branch is None:
            user_output(click.style("Error: ", fg="red") + "Could not detect trunk branch")
            raise SystemExit(1)

        # Trigger workflow and get run ID
        run_id = ctx.github.trigger_workflow(
            repo_root=repo.root,
            workflow="dispatch-erk-queue.yml",
            inputs={"issue_number": str(issue_number)},
            ref=trunk_branch,
        )

        # Extract owner and repo from issue URL
        # URL format: https://github.com/owner/repo/issues/123
        url_parts = issue.url.rstrip("/").split("/")
        if len(url_parts) >= 5 and url_parts[2] == "github.com":
            owner = url_parts[3]
            repo_name = url_parts[4]
            workflow_url = f"https://github.com/{owner}/{repo_name}/actions/runs/{run_id}"
        else:
            # Fallback if URL parsing fails
            workflow_url = f"(Run ID: {run_id})"

        user_output(click.style("✓", fg="green") + " Workflow triggered successfully")
        user_output("")
        user_output("Workflow started:")
        user_output(f"  {click.style(workflow_url, fg='cyan')}")
    except Exception as e:
        # Fail fast - abort the entire operation
        user_output("")
        user_output(click.style("✗ Failed to trigger workflow via API", fg="red"))
        user_output(f"  Error: {str(e)}")
        user_output("")
        user_output("Troubleshooting:")
        user_output("  • Check GitHub CLI authentication: gh auth status")
        user_output("  • Verify workflow dispatch permissions")
        user_output("  • Try manual submission: gh workflow run dispatch-erk-queue.yml")
        user_output("")
        user_output(f"Note: The {ERK_QUEUE_LABEL} label was still added to the issue.")
        user_output("The workflow may still be triggered via webhook, but this is not guaranteed.")
        raise SystemExit(1) from None

    # Gather submission metadata
    queued_at = datetime.now(UTC).isoformat()

    # Get submitter from git config
    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            check=True,
        )
        submitted_by = result.stdout.strip()
    except subprocess.CalledProcessError:
        # Fall back to "unknown" if git config fails
        submitted_by = "unknown"

    if not submitted_by:
        submitted_by = "unknown"

    validation_results = {
        "issue_is_open": True,
        "has_erk_plan_label": True,
        "no_erk_queue_label_before": True,
    }

    # Create and post queued event comment
    try:
        metadata_block = create_submission_queued_block(
            queued_at=queued_at,
            submitted_by=submitted_by,
            issue_number=issue_number,
            validation_results=validation_results,
            expected_workflow="dispatch-erk-queue",
        )

        comment_body = render_erk_issue_event(
            title="🔄 Issue Queued for Implementation",
            metadata=metadata_block,
            description=(
                f"Issue submitted by **{submitted_by}** at {queued_at}.\n\n"
                f"The `{ERK_QUEUE_LABEL}` label has been added. The GitHub Actions workflow "
                f"`dispatch-erk-queue` will be triggered automatically via webhook.\n\n"
                f"The workflow will:\n"
                f"- Create a branch from trunk\n"
                f"- Create `.erp/` folder with plan content\n"
                f"- Create a draft PR\n"
                f"- Run the implementation\n\n"
                f"Watch for the workflow start comment with a link to the action run."
            ),
        )

        user_output("Posting queued event comment...")
        ctx.issues.add_comment(repo.root, issue_number, comment_body)
        user_output(click.style("✓", fg="green") + " Queued event comment posted")
    except Exception as e:
        # Log warning but don't block workflow - label still triggers it
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"Failed to post queued comment: {e}\n"
            + "Workflow will still be triggered by label."
        )

    # Success output
    user_output("")
    user_output(click.style("✓", fg="green") + " Issue submitted successfully!")
    user_output("")
    user_output("Next steps:")
    user_output(f"  • View issue: {issue.url}")
    user_output("  • Monitor workflow progress at the link above")
    user_output("")
