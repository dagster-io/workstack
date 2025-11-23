"""Wrap a plan in a collapsible GitHub metadata block."""

import sys

import click


@click.command(name="wrap-plan-in-metadata-block")
def wrap_plan_in_metadata_block() -> None:
    """Wrap plan content in collapsible GitHub metadata block.

    Reads plan content from stdin and wraps it in a <details> block
    with erk-plan key for clean GitHub issue presentation.

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

    # Strip any leading/trailing whitespace
    plan_content = plan_content.strip()

    # Create intro text
    intro_text = "This issue contains an implementation plan:"

    # Create the collapsible block with plan markdown
    rendered_block = f"""<details>
<summary><code>erk-plan</code></summary>

{plan_content}
</details>"""

    # Output the complete issue body
    click.echo(intro_text)
    click.echo()
    click.echo(rendered_block)