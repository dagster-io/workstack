"""Format consistent error messages with brief, details, and actions.

This kit CLI command generates standardized error output with:
- Brief error description (5-10 words)
- Detailed error context
- Numbered list of 1-3 suggested actions

Usage:
    dot-agent kit-command erk format-error \\
        --brief "Brief description" \\
        --details "Detailed error message" \\
        --action "First suggested action" \\
        --action "Second suggested action"

Output:
    Formatted error message to stdout

Exit Codes:
    0: Success (errors are formatted output, not execution failures)

Examples:
    $ dot-agent kit-command erk format-error \\
        --brief "Plan content is too minimal" \\
        --details "Plan has only 50 characters (minimum 100 required)" \\
        --action "Provide a more detailed implementation plan" \\
        --action "Include specific tasks, steps, or phases"

    ❌ Error: Plan content is too minimal

    Details: Plan has only 50 characters (minimum 100 required)

    Suggested actions:
      1. Provide a more detailed implementation plan
      2. Include specific tasks, steps, or phases
"""

import click

from dot_agent_kit.data.kits.erk.plan_utils import format_error


@click.command(name="format-error")
@click.option(
    "--brief",
    required=True,
    type=str,
    help="Brief error description (5-10 words recommended)",
)
@click.option(
    "--details",
    required=True,
    type=str,
    help="Specific error message or context",
)
@click.option(
    "--action",
    "actions",
    multiple=True,
    required=True,
    type=str,
    help="Suggested action (repeatable, 1-3 recommended)",
)
def format_error_cli(brief: str, details: str, actions: tuple[str, ...]) -> None:
    """Format standardized error message with brief, details, and actions.

    Generates consistent error output following the template:
    - ❌ Error: {brief}
    - Details: {details}
    - Suggested actions: numbered list

    The --action option can be repeated to provide multiple suggestions.
    """
    # Convert tuple to list for the utility function
    actions_list = list(actions)

    # Call the pure utility function
    error_message = format_error(brief, details, actions_list)

    click.echo(error_message)
