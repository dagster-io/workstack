"""Convert plan title to filename.

Usage:
    dot-agent kit-command erk issue-title-to-filename "Plan Title"

Single source of truth for filename transformation across:
- /erk:save-plan
- /erk:save-context-enriched-plan
- /erk:save-session-enriched-plan
- issue-wt-creator agent

Output:
    Filename on stdout (e.g., "my-feature-plan.md")
    Error message on stderr with exit code 1 on failure

Exit Codes:
    0: Success
    1: Error (empty title)
"""

import re
import unicodedata

import click


def plan_title_to_filename(title: str) -> str:
    """Convert plan title to kebab-case filename.

    Comprehensive transformation matching /erk:save-context-enriched-plan:
    1. Lowercase
    2. Replace spaces with hyphens
    3. Unicode normalization (NFC)
    4. Remove emojis and non-alphanumeric characters (except hyphens)
    5. Collapse consecutive hyphens
    6. Strip leading/trailing hyphens
    7. Validate at least one alphanumeric character remains
    8. Append "-plan.md"

    NO truncation - erk create handles via sanitize_worktree_name().

    Returns "plan.md" if title is empty after cleanup.

    Args:
        title: Plan title to convert

    Returns:
        Filename with -plan.md suffix

    Examples:
        >>> plan_title_to_filename("Replace gt sync with targeted restack")
        'replace-gt-sync-with-targeted-restack-plan.md'
        >>> plan_title_to_filename("Fix: Bug #123")
        'fix-bug-123-plan.md'
        >>> plan_title_to_filename("🚀 Feature Launch 🎉")
        'feature-launch-plan.md'
        >>> plan_title_to_filename("café")
        'cafe-plan.md'
        >>> plan_title_to_filename("👨‍👩‍👧‍👦 Family Plan")
        'family-plan-plan.md'
    """
    # Step 1: Lowercase and strip whitespace
    lowered = title.strip().lower()

    # Step 2: Unicode normalization (NFD form for decomposition)
    # Decompose combined characters (é → e + ´)
    normalized = unicodedata.normalize("NFD", lowered)

    # Step 3: Remove emojis and non-ASCII characters, convert to ASCII
    # Keep only ASCII alphanumeric, spaces, and hyphens
    cleaned = ""
    for char in normalized:
        # Keep ASCII alphanumeric, spaces, and hyphens
        if ord(char) < 128 and (char.isalnum() or char in (" ", "-")):
            cleaned += char
        # Skip combining marks (accents) and emoji
        # Skip non-ASCII characters (CJK, emoji, special symbols)

    # Step 4: Replace spaces with hyphens
    replaced = cleaned.replace(" ", "-")

    # Step 5: Collapse consecutive hyphens
    collapsed = re.sub(r"-+", "-", replaced)

    # Step 6: Strip leading/trailing hyphens
    trimmed = collapsed.strip("-")

    # Step 7: Validate at least one alphanumeric character
    if not trimmed or not any(c.isalnum() for c in trimmed):
        return "plan.md"

    return f"{trimmed}-plan.md"


@click.command(name="issue-title-to-filename")
@click.argument("title")
def issue_title_to_filename(title: str) -> None:
    """Convert plan title to filename.

    TITLE: Plan title to convert
    """
    if not title or not title.strip():
        click.echo(click.style("Error: ", fg="red") + "Plan title cannot be empty", err=True)
        raise SystemExit(1)

    filename = plan_title_to_filename(title)
    click.echo(filename)
