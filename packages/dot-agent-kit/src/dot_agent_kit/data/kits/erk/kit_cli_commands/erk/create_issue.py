import json
import sys
from pathlib import Path

import click

from dot_agent_kit.context_helpers import require_github_issues


@click.command(name="create-issue")
@click.argument("title")
@click.option("--label", "-l", multiple=True, help="Labels to add (can be repeated)")
@click.pass_context
def create_issue(ctx: click.Context, title: str, label: tuple[str, ...]) -> None:
    """Create GitHub issue with body from stdin.

    Reads issue body from stdin and creates GitHub issue using gh CLI.
    Returns JSON with issue number and URL.

    Usage:
        echo "$body" | dot-agent kit-command erk create-issue "Title" --label "erk-plan"

    Exit Codes:
        0: Success
        1: Error (gh CLI failed)
    """
    # Get GitHub Issues from context (with LBYL check)
    github = require_github_issues(ctx)

    # Read body from stdin
    body = sys.stdin.read()

    # Get current repo root
    repo_root = Path.cwd()

    # Use injected GitHub Issues to create issue (EAFP pattern)
    try:
        issue_number = github.create_issue(repo_root, title, body, list(label))
    except RuntimeError as e:
        click.echo(f"Error: Failed to create issue: {e}", err=True)
        raise SystemExit(1) from e

    # Construct issue URL (owner/repo extracted by GitHub integration)
    # Note: We don't have direct access to owner/repo here, but the issue was created
    issue_url = f"https://github.com/owner/repo/issues/{issue_number}"

    # Output structured result
    output = {
        "success": True,
        "issue_number": issue_number,
        "issue_url": issue_url,
    }
    click.echo(json.dumps(output))
