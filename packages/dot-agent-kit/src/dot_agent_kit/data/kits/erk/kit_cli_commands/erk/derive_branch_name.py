"""Derive branch name from issue title.

This kit CLI command converts an issue title to a branch name using the
same logic as the erk CLI, ensuring consistency between local and remote
branch name derivation.

Usage:
    dot-agent run erk derive-branch-name <issue-title>

Output:
    The derived branch name with date suffix (no newline)

Exit Codes:
    0: Success

Examples:
    $ dot-agent run erk derive-branch-name "Implement feature X"
    implement-feature-x-25-11-29-1430

    $ dot-agent run erk derive-branch-name "Fix Bug #123!"
    fix-bug-123-25-11-29-1430
"""

import click
from erk_shared.naming import derive_branch_name_with_date


@click.command(name="derive-branch-name")
@click.argument("title")
def derive_branch_name(title: str) -> None:
    """Derive a branch name with date suffix from an issue title.

    Converts the title to kebab-case with datetime suffix, truncated
    to 30 characters (before suffix) for worktree compatibility. Uses
    the same logic as the local erk CLI to ensure consistency.

    TITLE: The issue title to convert to a branch name
    """
    branch_name = derive_branch_name_with_date(title)
    # No newline for easy shell capture
    click.echo(branch_name, nl=False)
