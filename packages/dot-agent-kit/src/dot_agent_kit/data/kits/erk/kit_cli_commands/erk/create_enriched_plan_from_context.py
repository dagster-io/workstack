"""Create GitHub issue from enriched plan (via --plan-file option).

This kit CLI command is used by the /erk:plan-save slash command which handles
plan enrichment before passing the enriched plan to this command via a file.

The enrichment happens in the agent's logic (adding context, architectural notes, etc.)
before calling this command. This command simply creates the issue from whatever
plan content it receives via the --plan-file option.

SCHEMA VERSION 2: This command uses the new two-step creation flow:
1. Create issue with metadata-only body (using format_plan_header_body())
2. Add first comment with plan content (using format_plan_content_comment())

This separates concerns: metadata in body (fast querying), content in comment.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import click
from erk_shared.github.metadata import (
    format_plan_content_comment,
    format_plan_header_body,
)
from erk_shared.naming import sanitize_worktree_name
from erk_shared.plan_utils import extract_title_from_plan

from dot_agent_kit.context_helpers import require_github_issues, require_repo_root


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
    creates issue with metadata body, then adds plan as first comment.

    Schema Version 2 format:
    - Issue body: metadata-only (schema_version, created_at, created_by, worktree_name)
    - First comment: plan content wrapped in markers

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

    # Get GitHub username for created_by field (via integration layer)
    username = github.get_current_username()
    if username is None:
        click.echo("Error: Could not get GitHub username (gh CLI not authenticated?)", err=True)
        raise SystemExit(1)

    # Derive worktree name from title
    worktree_name = sanitize_worktree_name(title)

    # Generate timestamp
    created_at = datetime.now(UTC).isoformat()

    # Format metadata-only body (schema version 2)
    formatted_body = format_plan_header_body(
        created_at=created_at,
        created_by=username,
        worktree_name=worktree_name,
    )

    # Ensure erk-plan label exists (required for erk submit validation)
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

    # Step 1: Create issue with metadata-only body and erk-plan label
    try:
        result = github.create_issue(repo_root, title, formatted_body, labels=["erk-plan"])
    except RuntimeError as e:
        click.echo(f"Error: Failed to create GitHub issue: {e}", err=True)
        raise SystemExit(1) from e

    # Step 2: Add first comment with plan content
    plan_comment = format_plan_content_comment(plan.strip())
    try:
        github.add_comment(repo_root, result.number, plan_comment)
    except RuntimeError as e:
        # Issue was created but comment failed - provide recovery info
        click.echo(
            f"Error: Issue #{result.number} created but failed to add plan comment: {e}\n"
            f"Please manually add plan content to: {result.url}",
            err=True,
        )
        raise SystemExit(1) from e

    # Output structured JSON
    output = {
        "success": True,
        "issue_number": result.number,
        "issue_url": result.url,
    }
    click.echo(json.dumps(output))
