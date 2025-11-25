"""Submit issue for remote AI implementation via GitHub Actions."""

import subprocess
from datetime import UTC, datetime

import click
from erk_shared.github.metadata import create_submission_queued_block, render_erk_issue_event
from erk_shared.output.output import user_output

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext

ERK_PLAN_LABEL = "erk-plan"


def _construct_workflow_run_url(issue_url: str, run_id: str) -> str:
    """Construct GitHub Actions workflow run URL from issue URL and run ID.

    Args:
        issue_url: GitHub issue URL (e.g., https://github.com/owner/repo/issues/123)
        run_id: Workflow run ID

    Returns:
        Workflow run URL (e.g., https://github.com/owner/repo/actions/runs/1234567890)
    """
    # Extract owner/repo from issue URL
    # Pattern: https://github.com/owner/repo/issues/123
    parts = issue_url.split("/")
    if len(parts) >= 5:
        owner = parts[-4]
        repo = parts[-3]
        return f"https://github.com/{owner}/{repo}/actions/runs/{run_id}"
    return f"https://github.com/actions/runs/{run_id}"


@click.command("submit")
@click.argument("issue_number", type=int)
@click.pass_obj
def submit_cmd(ctx: ErkContext, issue_number: int) -> None:
    """Submit issue for remote AI implementation via GitHub Actions.

    Triggers the dispatch-erk-queue.yml GitHub Actions workflow via direct
    workflow dispatch for automated implementation.

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

    # Display issue details
    user_output("Submitting issue for automated implementation:")
    user_output(f"  Number: {click.style(f'#{issue_number}', fg='cyan')}")
    user_output(f"  Title:  {click.style(issue.title, fg='yellow')}")
    user_output(f"  State:  {click.style(issue.state, fg='green')}")
    user_output("")

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

    # Trigger workflow via direct dispatch
    user_output("Triggering dispatch-erk-queue workflow...")
    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow="dispatch-erk-queue.yml",
        inputs={
            "issue_number": str(issue_number),
            "submitted_by": submitted_by,
        },
    )
    user_output(click.style("✓", fg="green") + " Workflow triggered.")

    validation_results = {
        "issue_is_open": True,
        "has_erk_plan_label": True,
    }

    # Create and post queued event comment
    workflow_url = _construct_workflow_run_url(issue.url, run_id)
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
                f"The `dispatch-erk-queue` workflow has been triggered via direct dispatch.\n\n"
                f"**Workflow run:** {workflow_url}\n\n"
                f"The workflow will:\n"
                f"- Create a branch from trunk\n"
                f"- Create `.erp/` folder with plan content\n"
                f"- Create a draft PR\n"
                f"- Run the implementation"
            ),
        )

        user_output("Posting queued event comment...")
        ctx.issues.add_comment(repo.root, issue_number, comment_body)
        user_output(click.style("✓", fg="green") + " Queued event comment posted")
    except Exception as e:
        # Log warning but don't block - workflow is already triggered
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"Failed to post queued comment: {e}\n"
            + "Workflow is already running."
        )

    # Success output
    user_output("")
    user_output(click.style("✓", fg="green") + " Issue submitted successfully!")
    user_output("")
    user_output("Next steps:")
    user_output(f"  • View issue: {issue.url}")
    user_output(f"  • View workflow run: {workflow_url}")
    user_output("")
