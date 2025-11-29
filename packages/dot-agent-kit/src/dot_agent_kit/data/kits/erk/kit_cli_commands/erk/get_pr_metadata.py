#!/usr/bin/env python3
"""Get PR metadata footer section for PR body.

This command builds a metadata footer section for PR bodies containing:
- Horizontal rule separator (at start of footer)
- Checkout command (with PR number or placeholder)
- Closes reference (if issue exists)

This footer is appended AFTER the PR body content, not before.

Usage:
    # Get metadata section without PR number (uses placeholder)
    pr_metadata=$(dot-agent run erk get-pr-metadata 2>/dev/null || echo "")

    # Get metadata section with actual PR number
    pr_metadata=$(dot-agent run erk get-pr-metadata --pr-number 123 2>/dev/null || echo "")

Output:
    - If issue reference exists: Formatted metadata footer section
    - If no issue reference: empty string (no output)

Exit Codes:
    0: Success (always succeeds, even if no metadata)

Examples:
    $ cd worktree-with-issue
    $ dot-agent run erk get-pr-metadata
    ---

    To checkout this PR in a fresh worktree and environment locally, run:

    ```
    erk pr checkout 123
    ```

    Closes #123

    $ cd worktree-without-issue
    $ dot-agent run erk get-pr-metadata
    (no output)
"""

from pathlib import Path

import click


@click.command(name="get-pr-metadata")
@click.option(
    "--pr-number",
    type=int,
    default=None,
    help="PR number for checkout command (uses placeholder if not provided)",
)
def get_pr_metadata(pr_number: int | None) -> None:
    """Get PR metadata footer section for PR body.

    Builds metadata footer section from .impl/ directory contents:
    - Issue reference from .impl/issue.json (required)
    - Checkout command with PR number or placeholder
    - Closes reference linking to the issue

    This footer is appended AFTER the PR body content.
    This command is designed for use in PR creation workflows where metadata
    is optional functionality that should degrade gracefully.
    """
    from erk_shared.impl_folder import get_closing_text

    impl_dir = Path.cwd() / ".impl"

    # Get closing text using canonical function
    closing_text = get_closing_text(impl_dir)

    # Only build metadata if we have an issue reference
    if not closing_text:
        return

    metadata_parts: list[str] = []

    # Separator at start of footer
    metadata_parts.append("\n---\n")

    # Checkout command (with placeholder or actual number)
    pr_display = str(pr_number) if pr_number is not None else "__PLACEHOLDER_PR_NUMBER__"
    metadata_parts.append(
        f"\nTo checkout this PR in a fresh worktree and environment locally, run:\n\n"
        f"```\n"
        f"erk pr checkout {pr_display}\n"
        f"```\n"
    )

    # Closes #N - use canonical closing text
    metadata_parts.append(f"\n{closing_text}\n")

    # Output metadata section
    output = "\n".join(metadata_parts)
    click.echo(output, nl=False)
