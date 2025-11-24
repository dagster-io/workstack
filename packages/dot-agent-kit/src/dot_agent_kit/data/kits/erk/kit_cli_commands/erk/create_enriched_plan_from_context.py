"""Create GitHub issue from enriched plan (via --plan-file option) with erk-plan label.

This kit CLI command is used by the /erk:save-plan slash command which handles
plan enrichment before passing the enriched plan to this command via a file.

The enrichment happens in the agent's logic (adding context, architectural notes, etc.)
before calling this command. This command simply creates the issue from whatever
plan content it receives via the --plan-file option.
"""

import json
from pathlib import Path

import click
from erk_shared.github.metadata import format_plan_issue_body

from dot_agent_kit.context_helpers import require_github_issues, require_repo_root
from erk.data.kits.erk.plan_utils import extract_title_from_plan


@click.command(name="create-enriched-plan-from-context")
@click.option(
    "--plan-file",
    required=True,
    type=click.Path(exists=True),
    help="Path to file containing plan content",
)
@click.pass_context
def create_enriched_plan_from_context(ctx: click.Context, plan_file: str) -> None:
    """Create GitHub issue from enriched plan (via --plan-file option).

    Reads enriched plan content from file, extracts title,
    ensures erk-plan label exists, creates issue, and returns JSON result.

    The plan should already be enriched by the calling agent before being passed
    to this command.

    Usage:
        dot-agent kit-command erk create-enriched-plan-from-context \\
            --plan-file /tmp/enriched_plan.md

    Exit Codes:
        0: Success
        1: Error (empty plan, gh failure, etc.)

    Output:
        JSON object: {"success": true, "issue_number": 123, "issue_url": "..."}
    """
    # Get GitHub Issues from context (LBYL check in helper)
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Read plan content from file (LBYL: click.Path(exists=True) already validated)
    plan_path = Path(plan_file)
    plan = plan_path.read_text(encoding="utf-8")

    # Validate plan not empty
    if not plan or not plan.strip():
        click.echo("Error: Empty plan content in file", err=True)
        raise SystemExit(1)

    # Extract title (pure function call)
    title = extract_title_from_plan(plan)

    # Plan content is used as-is for the issue body
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
        result = github.create_issue(repo_root, title, body, ["erk-plan"])
    except RuntimeError as e:
        click.echo(f"Error: Failed to create GitHub issue: {e}", err=True)
        raise SystemExit(1) from e

    # Format body with collapsible details and execution commands
    formatted_body = format_plan_issue_body(plan.strip(), result.number)

    # Update issue with formatted body
    try:
        github.update_issue_body(repo_root, result.number, formatted_body)
    except RuntimeError as e:
        click.echo(f"Error: Failed to update issue body: {e}", err=True)
        raise SystemExit(1) from e

    # Output structured JSON
    output = {
        "success": True,
        "issue_number": result.number,
        "issue_url": result.url,
    }
    click.echo(json.dumps(output))
