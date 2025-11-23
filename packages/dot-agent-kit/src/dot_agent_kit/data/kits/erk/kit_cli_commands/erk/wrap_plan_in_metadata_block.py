"""Wrap a plan in a collapsible GitHub metadata block."""

import sys

import click

from dot_agent_kit.data.kits.erk.plan_utils import wrap_plan_in_metadata_block as _wrap


@click.command(name="wrap-plan-in-metadata-block")
def wrap_plan_in_metadata_block() -> None:
    """Return plan content for issue body.

    Reads plan content from stdin and returns it as-is.
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

    # Call pure function
    result = _wrap(plan_content)

    # Output the result
    click.echo(result)
