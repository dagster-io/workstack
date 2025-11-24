"""Create .erp/ folder from GitHub issue with plan content.

This kit CLI command fetches a plan from a GitHub issue and creates the .erp/
folder structure, providing a testable alternative to inline workflow scripts.

Usage:
    dot-agent run erk create-erp-from-issue <issue-number> <issue-title>

Output:
    Structured JSON output with success status and folder details

Exit Codes:
    0: Success (.erp/ folder created)
    1: Error (issue not found, plan fetch failed, folder creation failed)

Examples:
    $ dot-agent run erk create-erp-from-issue 1028 "Improve CLI output list format"
    {"success": true, "erp_path": "/path/to/.erp", "issue_number": 1028}

    $ dot-agent run erk create-erp-from-issue 999 "Missing Issue"
    {"success": false, "error": "issue_not_found", "message": "..."}
"""

import json

import click
from erk_shared.erp_folder import create_erp_folder

from dot_agent_kit.context_helpers import require_github_issues, require_repo_root


@click.command(name="create-erp-from-issue")
@click.argument("issue_number", type=int)
@click.argument("issue_title")
@click.pass_context
def create_erp_from_issue(
    ctx: click.Context,
    issue_number: int,
    issue_title: str,
) -> None:
    """Create .erp/ folder from GitHub issue with plan content.

    Fetches plan content from GitHub issue and creates .erp/ folder structure
    with plan.md, issue.json, and metadata.

    ISSUE_NUMBER: GitHub issue number containing the plan
    ISSUE_TITLE: Title of the GitHub issue
    """
    # Get GitHub Issues from context (LBYL check in helper)
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)

    # Fetch issue from GitHub (raises RuntimeError if not found)
    try:
        issue = github.get_issue(repo_root, issue_number)
    except RuntimeError as e:
        error_output = {
            "success": False,
            "error": "issue_not_found",
            "message": f"Could not fetch issue #{issue_number}: {e}",
        }
        click.echo(json.dumps(error_output), err=True)
        raise SystemExit(1) from e

    # Validate issue has erk-plan label
    if "erk-plan" not in issue.labels:
        error_output = {
            "success": False,
            "error": "missing_erk_plan_label",
            "message": f"Issue #{issue_number} does not have 'erk-plan' label. "
            f"Ensure issue has erk-plan label.",
        }
        click.echo(json.dumps(error_output), err=True)
        raise SystemExit(1)

    # Create .erp/ folder with plan content
    erp_path = repo_root / ".erp"
    create_erp_folder(
        plan_content=issue.body,
        issue_number=issue_number,
        issue_url=issue.url,
        issue_title=issue_title,
        repo_root=repo_root,
    )

    # Output structured success result
    output = {
        "success": True,
        "erp_path": str(erp_path),
        "issue_number": issue_number,
        "issue_url": issue.url,
    }
    click.echo(json.dumps(output))
