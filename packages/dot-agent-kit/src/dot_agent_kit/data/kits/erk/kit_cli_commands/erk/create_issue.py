import json
import sys

import click

from dot_agent_kit.context_helpers import require_github_cli


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
    # Get GitHub CLI from context (with LBYL check)
    github_cli = require_github_cli(ctx)

    # Read body from stdin
    body = sys.stdin.read()

    # Use injected GitHub CLI to create issue
    result = github_cli.create_issue(title, body, list(label))

    # Check for errors (LBYL pattern)
    if not result.success:
        click.echo("Error: Failed to create issue", err=True)
        raise SystemExit(1)

    # Output structured result
    output = {
        "success": True,
        "issue_number": result.issue_number,
        "issue_url": result.issue_url,
    }
    click.echo(json.dumps(output))
