"""Return plan content for issue body without wrapping."""

import sys

import click


@click.command(name="wrap-plan-in-metadata-block")
def wrap_plan_in_metadata_block() -> None:
    """Return plan content for issue body.

    Reads plan content from stdin and returns it as-is (stripped of leading/trailing whitespace).
    Formatting and workflow instructions will be added via a separate comment.

    Usage:
        echo "$plan" | dot-agent kit-command erk wrap-plan-in-metadata-block

    Exit Codes:
        0: Success
        1: Error (empty input)
    """
    # Read plan content from stdin
    plan_content = sys.stdin.read()

    # Validate input is not empty
    if not plan_content or not plan_content.strip():
        click.echo("Error: Empty plan content received", err=True)
        raise SystemExit(1)

    # Return plan content as-is (stripped)
    # Metadata wrapping now happens via separate GitHub comments
    click.echo(plan_content.strip())
