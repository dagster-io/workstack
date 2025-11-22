"""Convert GitHub issue title to plan filename.

Usage:
    dot-agent kit-command erk issue-title-to-filename "Issue Title"

Output:
    Filename on stdout (e.g., "my-feature-plan.md")
    Error message on stderr with exit code 1 on failure

Exit Codes:
    0: Success
    1: Error (empty title)
"""

import re

import click


def title_to_filename(title: str) -> str:
    """Convert issue title to kebab-case filename.

    Matches /erk:save-plan transformation logic (Step 2):
    1. Lowercase
    2. Replace non-alphanumeric with hyphens
    3. Collapse consecutive hyphens
    4. Strip leading/trailing hyphens
    5. Append "-plan.md"

    NO truncation - erk create handles via sanitize_worktree_name().

    Returns "plan.md" if title is empty after cleanup.

    Args:
        title: GitHub issue title to convert

    Returns:
        Filename with -plan.md suffix

    Examples:
        >>> title_to_filename("Replace gt sync with targeted restack")
        'replace-gt-sync-with-targeted-restack-plan.md'
        >>> title_to_filename("Fix: Bug #123")
        'fix-bug-123-plan.md'
        >>> title_to_filename("🚀 Feature!")
        'feature-plan.md'
    """
    lowered = title.strip().lower()
    replaced = re.sub(r"[^a-z0-9-]+", "-", lowered)
    collapsed = re.sub(r"-+", "-", replaced)
    trimmed = collapsed.strip("-")

    if not trimmed:
        return "plan.md"

    return f"{trimmed}-plan.md"


@click.command(name="issue-title-to-filename")
@click.argument("title")
def issue_title_to_filename(title: str) -> None:
    """Convert GitHub issue title to plan filename.

    TITLE: GitHub issue title to convert
    """
    if not title or not title.strip():
        click.echo(click.style("Error: ", fg="red") + "Issue title cannot be empty", err=True)
        raise SystemExit(1)

    filename = title_to_filename(title)
    click.echo(filename)
