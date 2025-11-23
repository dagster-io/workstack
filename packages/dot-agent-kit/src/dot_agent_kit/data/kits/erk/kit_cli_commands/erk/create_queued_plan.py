"""Create GitHub issue with erk-queue label from plan file.

This kit CLI command is a specialized wrapper around create_plan_issue_from_plan_file
that specifically uses the erk-queue label for automatic implementation queues.

The erk-queue label is used to mark issues that should be automatically implemented
by the erk system, as opposed to erk-plan which is for manual execution.
"""

import json
from pathlib import Path

import click

from dot_agent_kit.context_helpers import require_github_cli
from dot_agent_kit.data.kits.erk.plan_utils import extract_title_from_plan


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
    # Get GitHub CLI from context (LBYL check in helper)
    github_cli = require_github_cli(ctx)

    # Read file (Python file I/O, not shell)
    plan = plan_file.read_text(encoding="utf-8")

    # Validate plan not empty
    if not plan or not plan.strip():
        click.echo(f"Error: Plan file is empty: {plan_file}", err=True)
        raise SystemExit(1)

    # Extract title and prepare body (pure functions)
    title = extract_title_from_plan(plan)
    body = plan.strip()

    # Ensure erk-queue label exists
    _label_result = github_cli.ensure_label_exists(
        label="erk-queue",
        description="Automatic implementation queue",
        color="0E8A16",
    )

    # Create issue with erk-queue label
    result = github_cli.create_issue(title, body, ["erk-queue"])

    # Check result (LBYL pattern)
    if not result.success:
        click.echo("Error: Failed to create issue", err=True)
        raise SystemExit(1)

    # Return JSON
    output = {
        "success": True,
        "issue_number": result.issue_number,
        "issue_url": result.issue_url,
    }
    click.echo(json.dumps(output))
