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

from dot_agent_kit.context_helpers import require_github_issues, require_repo_root
from erk.data.kits.erk.plan_utils import extract_title_from_plan


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
    # Get GitHub Issues from context (LBYL check in helper)
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

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

    # Ensure label exists (ABC interface with EAFP pattern)
    try:
        github.ensure_label_exists(
            repo_root=repo_root,
            label="erk-plan",
            description="Implementation plan for manual execution",
            color="0E8A16",
        )
    except RuntimeError as e:
        click.echo(f"Error: Failed to ensure label exists: {e}", err=True)
        raise SystemExit(1) from e

    # Create issue (ABC interface with EAFP pattern)
    try:
        issue_number = github.create_issue(repo_root, title, body, ["erk-plan"])
    except RuntimeError as e:
        click.echo(f"Error: Failed to create GitHub issue: {e}", err=True)
        raise SystemExit(1) from e

    # Construct issue URL (owner/repo extracted by GitHub integration)
    issue_url = f"https://github.com/owner/repo/issues/{issue_number}"

    # Output structured JSON
    output = {
        "success": True,
        "issue_number": issue_number,
        "issue_url": issue_url,
    }
    click.echo(json.dumps(output))
