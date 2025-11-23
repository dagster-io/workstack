"""Create GitHub issue from plan content (via stdin) with erk-plan label.

This kit CLI command handles the complete workflow for creating a plan issue:
1. Read plan from stdin
2. Extract title from plan
3. Ensure erk-plan label exists
4. Create GitHub issue with plan body and label
5. Return structured JSON result

This replaces the complex shell orchestration in the slash command with a single,
well-tested Python command that uses the ABC interface for GitHub operations.
"""

import json
import sys

import click

from dot_agent_kit.context_helpers import require_github_cli
from dot_agent_kit.data.kits.erk.plan_utils import extract_title_from_plan


@click.command(name="create-plan-issue-from-context")
@click.pass_context
def create_plan_issue_from_context(ctx: click.Context) -> None:
    """Create GitHub issue from plan content with erk-plan label.

    Reads plan content from stdin, extracts title, ensures erk-plan label exists,
    creates issue, and returns JSON result.

    Usage:
        echo "$plan" | dot-agent kit-command erk create-plan-issue-from-context

    Exit Codes:
        0: Success
        1: Error (empty plan, gh failure, etc.)

    Output:
        JSON object: {"success": true, "issue_number": 123, "issue_url": "..."}
    """
    # Get GitHub CLI from context (LBYL check in helper)
    github_cli = require_github_cli(ctx)

    # Read plan from stdin
    plan = sys.stdin.read()

    # Validate plan not empty
    if not plan or not plan.strip():
        click.echo("Error: Empty plan content received", err=True)
        raise SystemExit(1)

    # Extract title (pure function call)
    title = extract_title_from_plan(plan)

    # Plan content is used as-is for the issue body
    # Metadata tracking happens via separate comments using render_erk_issue_event()
    body = plan.strip()

    # Ensure label exists (ABC interface)
    _label_result = github_cli.ensure_label_exists(
        label="erk-plan",
        description="Implementation plan for manual execution",
        color="0E8A16",
    )
    # Note: label_result is intentionally unused - we don't need to check it
    # The ensure_label_exists method is non-blocking even if it fails

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
