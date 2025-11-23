"""Create GitHub issue with erk-queue label from plan file.

This kit CLI command is a specialized wrapper around create_plan_issue_from_plan_file
that specifically uses the erk-queue label for automatic implementation queues.

The erk-queue label is used to mark issues that should be automatically implemented
by the erk system, as opposed to erk-plan which is for manual execution.
"""

import json
from pathlib import Path

import click

from dot_agent_kit.context_helpers import require_github_issues, require_repo_root
from erk.data.kits.erk.plan_utils import extract_title_from_plan


@click.command(name="create-queued-plan")
@click.argument("plan_file", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def create_queued_plan(
    ctx: click.Context,
    plan_file: Path,
) -> None:
    """Create GitHub issue with erk-queue label for automatic implementation.

    PLAN_FILE: Path to *-plan.md file

    This command uses the erk-queue label instead of erk-plan to indicate
    that the issue should be automatically implemented by the erk system.

    Exit Codes:
        0: Success
        1: Error (file not found, gh failure, etc.)

    Output:
        JSON object: {"success": true, "issue_number": 123, "issue_url": "..."}

    Usage:
        dot-agent kit-command erk create-queued-plan my-feature-plan.md
    """
    # Get GitHub Issues from context (LBYL check in helper)
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Read file (Python file I/O, not shell)
    plan = plan_file.read_text(encoding="utf-8")

    # Validate plan not empty
    if not plan or not plan.strip():
        click.echo(f"Error: Plan file is empty: {plan_file}", err=True)
        raise SystemExit(1)

    # Extract title and prepare body (pure functions)
    title = extract_title_from_plan(plan)
    body = plan.strip()

    # Ensure erk-queue label exists (EAFP pattern)
    try:
        github.ensure_label_exists(
            repo_root=repo_root,
            label="erk-queue",
            description="Automatic implementation queue",
            color="0E8A16",
        )
    except RuntimeError as e:
        click.echo(f"Error: Failed to ensure label exists: {e}", err=True)
        raise SystemExit(1) from e

    # Create issue with erk-queue label (EAFP pattern)
    try:
        issue_number = github.create_issue(repo_root, title, body, ["erk-queue"])
    except RuntimeError as e:
        click.echo(f"Error: Failed to create issue: {e}", err=True)
        raise SystemExit(1) from e

    # Construct issue URL (owner/repo extracted by GitHub integration)
    issue_url = f"https://github.com/owner/repo/issues/{issue_number}"

    # Return JSON
    output = {
        "success": True,
        "issue_number": issue_number,
        "issue_url": issue_url,
    }
    click.echo(json.dumps(output))
