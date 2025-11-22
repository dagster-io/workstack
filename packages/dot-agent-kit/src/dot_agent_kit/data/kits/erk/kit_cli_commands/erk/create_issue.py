import json
import re
import subprocess
import sys

import click


@click.command(name="create-issue")
@click.argument("title")
@click.option("--label", "-l", multiple=True, help="Labels to add (can be repeated)")
def create_issue(title: str, label: tuple[str, ...]) -> None:
    """Create GitHub issue with body from stdin.

    Reads issue body from stdin and creates GitHub issue using gh CLI.
    Returns JSON with issue number and URL.

    Usage:
        echo "$body" | dot-agent kit-command erk create-issue "Title" --label "erk-plan"

    Exit Codes:
        0: Success
        1: Error (gh CLI failed)
    """
    # Read body from stdin
    body = sys.stdin.read()

    # Build gh command with labels - use --body-file - to read from stdin
    cmd = ["gh", "issue", "create", "--title", title, "--body-file", "-"]
    for lbl in label:
        cmd.extend(["--label", lbl])

    # Execute gh with body via stdin
    result = subprocess.run(
        cmd,
        input=body,
        capture_output=True,
        text=True,
        check=False,
    )

    # Check for errors
    if result.returncode != 0:
        click.echo(f"Error: {result.stderr}", err=True)
        raise SystemExit(1)

    # Parse URL from output (gh returns: https://github.com/owner/repo/issues/123)
    issue_url = result.stdout.strip()

    # Extract issue number from URL
    match = re.search(r"/issues/(\d+)$", issue_url)
    if not match:
        click.echo(f"Error: Could not parse issue number from URL: {issue_url}", err=True)
        raise SystemExit(1)

    issue_number = int(match.group(1))

    # Output structured result
    output = {
        "success": True,
        "issue_number": issue_number,
        "issue_url": issue_url,
    }
    click.echo(json.dumps(output))
