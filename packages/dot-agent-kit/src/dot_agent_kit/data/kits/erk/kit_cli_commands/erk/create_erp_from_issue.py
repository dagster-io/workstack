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
from pathlib import Path

import click
from erk.core.context import create_context
from erk_shared.erp_folder import create_erp_folder


@click.command(name="create-erp-from-issue")
@click.argument("issue_number", type=int)
@click.argument("issue_title")
@click.option(
    "--repo-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Repository root directory (defaults to current directory)",
)
def create_erp_from_issue(
    issue_number: int,
    issue_title: str,
    repo_root: Path | None,
) -> None:
    """Create .erp/ folder from GitHub issue with plan content.

    Fetches plan content from GitHub issue and creates .erp/ folder structure
    with plan.md, issue.json, and metadata.

    ISSUE_NUMBER: GitHub issue number containing the plan
    ISSUE_TITLE: Title of the GitHub issue
    """
    # Default to current directory if not specified
    if repo_root is None:
        repo_root = Path.cwd()

    # Create context to access plan store
    # Use script=True to suppress diagnostic output in CI environments
    ctx = create_context(dry_run=False, script=True)

    # Fetch plan from GitHub (raises RuntimeError if not found)
    try:
        plan = ctx.plan_store.get_plan(repo_root, str(issue_number))
    except RuntimeError as e:
        error_output = {
            "success": False,
            "error": "plan_not_found",
            "message": f"Could not fetch plan for issue #{issue_number}: {e}. "
            f"Ensure issue has erk-plan label and plan content.",
        }
        click.echo(json.dumps(error_output), err=True)
        raise SystemExit(1) from e

    # Create .erp/ folder with plan content
    erp_path = repo_root / ".erp"
    create_erp_folder(
        plan_content=plan.body,
        issue_number=issue_number,
        issue_url=plan.url,
        issue_title=issue_title,
        repo_root=repo_root,
    )

    # Output structured success result
    output = {
        "success": True,
        "erp_path": str(erp_path),
        "issue_number": issue_number,
        "issue_url": plan.url,
    }
    click.echo(json.dumps(output))
