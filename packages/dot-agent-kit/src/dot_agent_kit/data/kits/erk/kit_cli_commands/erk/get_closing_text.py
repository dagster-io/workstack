#!/usr/bin/env python3
"""Get GitHub issue closing text for PR body.

This command checks if a worktree was created from a GitHub issue by looking for
`.impl/issue.json`. If found, it returns the "Closes #N" text that should be
prepended to PR bodies to automatically link and close the issue.

Usage:
    # Get closing text (if issue reference exists)
    closing_text=$(dot-agent run erk get-closing-text 2>/dev/null || echo "")

Output:
    - If issue reference exists: "Closes #123\n\n" (with trailing newlines)
    - If no issue reference: empty string (no output)

Exit Codes:
    0: Success (always succeeds, even if no issue reference)

Examples:
    $ cd worktree-with-issue
    $ dot-agent run erk get-closing-text
    Closes #776

    $ cd worktree-without-issue
    $ dot-agent run erk get-closing-text
    (no output)

Implementation:
    This replaces inline Python scripts in agent markdown with tested Python code.
    It provides cleaner agent code and makes issue linking behavior testable.
"""

from pathlib import Path

import click


@click.command(name="get-closing-text")
def get_closing_text_cmd() -> None:
    """Get GitHub issue closing text for PR body.

    Checks for `.impl/issue.json` in current directory and returns the "Closes #N"
    text if found. Returns empty string (no output) if issue reference doesn't exist.

    This command is designed for use in PR creation workflows where issue linking
    is optional functionality that should degrade gracefully.
    """
    # Import here to avoid loading when not needed
    from erk_shared.impl_folder import get_closing_text

    impl_dir = Path.cwd() / ".impl"

    # Get closing text using canonical function
    closing_text = get_closing_text(impl_dir)
    if not closing_text:
        # No issue reference - return empty (no output)
        return

    # Output closing text (with trailing newlines for PR body formatting)
    click.echo(f"{closing_text}\n\n", nl=False)
