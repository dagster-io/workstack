"""Create GitHub issue from plan file on disk.

This kit CLI command creates a GitHub issue from a plan file stored on disk
(typically created by /erk:save-plan or /erk:save-context-enriched-plan).

Handles the complete workflow:
1. Read plan file from disk
2. Extract title from plan
3. Ensure label exists (erk-plan by default, configurable via --label)
4. Create GitHub issue
5. Return structured JSON result
"""

import json
from pathlib import Path

import click

from dot_agent_kit.context_helpers import require_github_issues, require_repo_root
from dot_agent_kit.data.kits.erk.plan_utils import extract_title_from_plan


@click.command(name="create-plan-issue-from-plan-file")
@click.argument("plan_file", type=click.Path(exists=True, path_type=Path))
@click.option("--label", default="erk-plan", help="Label to apply to issue")
@click.pass_context
def create_plan_issue_from_plan_file(
    ctx: click.Context,
    plan_file: Path,
    label: str,
) -> None:
    """Create GitHub issue from plan file on disk.

    PLAN_FILE: Path to *-plan.md file

    Options:
        --label: Label to apply (default: erk-plan)

    Exit Codes:
        0: Success
        1: Error (file not found, gh failure, etc.)

    Output:
        JSON object: {"success": true, "issue_number": 123, "issue_url": "..."}

    Usage:
        dot-agent kit-command erk create-plan-issue-from-plan-file my-feature-plan.md
        dot-agent kit-command erk create-plan-issue-from-plan-file my-plan.md --label erk-queue
    """
    # Get GitHub Issues from context (LBYL check in helper)
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Read file (Python file I/O, not shell)
    # LBYL: path existence already checked by Click
    plan = plan_file.read_text(encoding="utf-8")

    # Validate plan not empty
    if not plan or not plan.strip():
        click.echo(f"Error: Plan file is empty: {plan_file}", err=True)
        raise SystemExit(1)

    # Extract title and prepare body (pure functions)
    title = extract_title_from_plan(plan)
    body = plan.strip()

    # Ensure label exists
    # Label description varies based on label type
    if label == "erk-queue":
        description = "Automatic implementation queue"
    else:
        description = "Implementation plan for manual execution"

    try:
        github.ensure_label_exists(
            repo_root=repo_root,
            label=label,
            description=description,
            color="0E8A16",
        )
    except RuntimeError as e:
        click.echo(f"Error: Failed to ensure label exists: {e}", err=True)
        raise SystemExit(1) from e

    # Create issue (ABC interface with EAFP pattern)
    try:
        issue_number = github.create_issue(repo_root, title, body, [label])
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
