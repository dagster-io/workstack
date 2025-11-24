"""Post GitHub issue workflow started comment with run URL.

This kit CLI command posts workflow started comments to GitHub issues using
collapsible <details> sections with machine-parsable YAML data.

Usage:
    dot-agent run erk post-workflow-started-comment \
        --issue-number 123 \
        --workflow-run-id 456789 \
        --workflow-run-url "https://github.com/..."

Output:
    JSON with success status or error information
    Always exits with code 0 (graceful degradation for || true pattern)

Exit Codes:
    0: Always (even on error, to support || true pattern)

Examples:
    $ dot-agent run erk post-workflow-started-comment \
        --issue-number 123 \
        --workflow-run-id 456789 \
        --workflow-run-url "https://github.com/org/repo/actions/runs/456789"
    {"success": true, "issue_number": 123}
"""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import click
from erk_shared.github.metadata import (
    create_workflow_started_block,
    render_erk_issue_event,
)

from dot_agent_kit.context_helpers import require_github_issues, require_repo_root


@dataclass(frozen=True)
class WorkflowStartedSuccess:
    """Success response for workflow started comment posting."""

    success: bool
    issue_number: int


@dataclass(frozen=True)
class WorkflowStartedError:
    """Error response for workflow started comment posting."""

    success: bool
    error_type: str
    message: str


@click.command(name="post-workflow-started-comment")
@click.option("--issue-number", required=True, type=int, help="GitHub issue number")
@click.option("--workflow-run-id", required=True, help="GitHub Actions run ID")
@click.option("--workflow-run-url", required=True, help="Full URL to workflow run")
@click.option("--branch-name", default=None, help="Optional git branch name")
@click.option("--worktree-path", default=None, help="Optional path to worktree")
@click.pass_context
def post_workflow_started_comment(
    ctx: click.Context,
    issue_number: int,
    workflow_run_id: str,
    workflow_run_url: str,
    branch_name: str | None,
    worktree_path: str | None,
) -> None:
    """Post workflow started comment to GitHub issue.

    Posts a comment with structured YAML data in a collapsible details section,
    including the workflow run URL for direct access to the GitHub Actions run.
    """
    # Get dependencies from context
    repo_root = require_repo_root(ctx)

    # Generate timestamp
    started_at = datetime.now(UTC).isoformat()

    # Create metadata block using shared library
    block = create_workflow_started_block(
        started_at=started_at,
        workflow_run_id=workflow_run_id,
        workflow_run_url=workflow_run_url,
        issue_number=issue_number,
        branch_name=branch_name,
        worktree_path=worktree_path,
    )

    # Create comment with consistent format
    comment_body = render_erk_issue_event(
        title="🚀 Workflow Started",
        metadata=block,
        description=(
            f"GitHub Actions workflow is now running.\n\n"
            f"**Workflow Run:** [{workflow_run_id}]({workflow_run_url})"
        ),
    )

    # Get GitHub Issues from context (with LBYL check)
    # Convert stderr error to JSON error for graceful degradation (|| true pattern)
    try:
        github = require_github_issues(ctx)
    except SystemExit:
        result = WorkflowStartedError(
            success=False,
            error_type="context_not_initialized",
            message="Context not initialized",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

    # Post comment to GitHub
    try:
        github.add_comment(repo_root, issue_number, comment_body)
        result = WorkflowStartedSuccess(
            success=True,
            issue_number=issue_number,
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None
    except RuntimeError as e:
        result = WorkflowStartedError(
            success=False,
            error_type="github_api_failed",
            message=str(e),
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None
