"""Format success output for GitHub issue creation.

This kit CLI command generates standardized success output after creating
a GitHub issue, including the issue link, next steps commands, and JSON metadata.

Usage:
    dot-agent kit-command erk format-success-output --issue-number 123 --issue-url "https://..."

Output:
    Formatted markdown with issue link, commands, and JSON footer

Exit Codes:
    0: Success

Examples:
    $ dot-agent kit-command erk format-success-output \\
        --issue-number 123 \\
        --issue-url "https://github.com/org/repo/issues/123"

    ✅ GitHub issue created: #123
    https://github.com/org/repo/issues/123

    Next steps:

    View Issue: gh issue view 123 --web
    Interactive Execution: erk implement 123
    Dangerous Interactive Execution: erk implement 123 --dangerous
    Yolo One Shot: erk implement 123 --yolo

    ---

    {
        "issue_number": 123,
        "issue_url": "https://github.com/org/repo/issues/123",
        "status": "created"
    }
"""

import json

import click


@click.command(name="format-success-output")
@click.option(
    "--issue-number",
    required=True,
    type=int,
    help="GitHub issue number",
)
@click.option(
    "--issue-url",
    required=True,
    type=str,
    help="Full GitHub issue URL",
)
def format_success_output(issue_number: int, issue_url: str) -> None:
    """Format standardized success output for GitHub issue creation.

    Generates consistent success message with:
    - Issue number and URL
    - Next steps commands (gh, erk implement variations)
    - JSON metadata footer
    """
    # Build the success output
    output_lines = [
        f"✅ GitHub issue created: #{issue_number}",
        issue_url,
        "",
        "Next steps:",
        "",
        f"View Issue: gh issue view {issue_number} --web",
        f"Interactive Execution: erk implement {issue_number}",
        f"Dangerous Interactive Execution: erk implement {issue_number} --dangerous",
        f"Yolo One Shot: erk implement {issue_number} --yolo",
        "",
        "---",
        "",
        json.dumps(
            {
                "issue_number": issue_number,
                "issue_url": issue_url,
                "status": "created",
            }
        ),
    ]

    click.echo("\n".join(output_lines))
