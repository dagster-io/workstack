"""Create GitHub issue from enriched plan (via stdin) with erk-plan label.

This kit CLI command is identical to create_plan_issue_from_context but is used
by the /erk:create-enriched-plan-issue-from-context slash command which handles
plan enrichment before passing the enriched plan to this command.

The enrichment happens in the agent's logic (adding context, architectural notes, etc.)
before calling this command. This command simply creates the issue from whatever
plan content it receives on stdin.
"""

import json
import sys

import click

from dot_agent_kit.context_helpers import require_github_cli
from dot_agent_kit.data.kits.erk.plan_utils import extract_title_from_plan


@click.command(name="create-enriched-plan-issue-from-context")
@click.pass_context
def create_enriched_plan_issue_from_context(ctx: click.Context) -> None:
    """Create GitHub issue from enriched plan (via stdin).

    Reads enriched plan content from stdin, extracts title, ensures erk-plan label
    exists, creates issue, and returns JSON result.

    The plan should already be enriched by the calling agent before being passed
    to this command.

    Usage:
        echo "$enriched_plan" | dot-agent kit-command erk create-enriched-plan-issue-from-context

    Exit Codes:
        0: Success
        1: Error (empty plan, gh failure, etc.)

    Output:
        JSON object: {"success": true, "issue_number": 123, "issue_url": "..."}
    """
    # Get GitHub CLI from context (LBYL check in helper)
    github_cli = require_github_cli(ctx)

    # Read enriched plan from stdin
    plan = sys.stdin.read()

    # Validate plan not empty
    if not plan or not plan.strip():
        click.echo("Error: Empty plan content received", err=True)
        raise SystemExit(1)

    # Extract title (pure function call)
    title = extract_title_from_plan(plan)

    # Plan content is used as-is for the issue body
    body = plan.strip()

    # Ensure label exists (ABC interface)
    _label_result = github_cli.ensure_label_exists(
        label="erk-plan",
        description="Implementation plan for manual execution",
        color="0E8A16",
    )

    # Create issue (ABC interface)
    result = github_cli.create_issue(title, body, ["erk-plan"])

    # Check result (LBYL pattern)
    if not result.success:
        click.echo("Error: Failed to create GitHub issue", err=True)
        raise SystemExit(1)

    # Output structured JSON
    output = {
        "success": True,
        "issue_number": result.issue_number,
        "issue_url": result.issue_url,
    }
    click.echo(json.dumps(output))
