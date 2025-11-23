"""Pure functions for plan manipulation and metadata.

This module contains reusable pure functions for working with implementation plans.
These functions are used by both kit CLI commands and internal logic, providing
a single source of truth for plan operations.

All functions follow LBYL (Look Before You Leap) patterns and have no external
dependencies or I/O operations.
"""

import re
import unicodedata


def wrap_plan_in_metadata_block(
    plan: str, intro_text: str = "This issue contains an implementation plan:"
) -> str:
    """Return plan content wrapped in collapsible details block for issue body.

    Wraps the full plan in a collapsible <details> block with customizable
    introductory text, making GitHub issues more scannable while preserving
    all plan details.

    Args:
        plan: Raw plan content as markdown string
        intro_text: Optional introductory text displayed before the collapsible
            block. Defaults to "This issue contains an implementation plan:"

    Returns:
        Plan wrapped in details block with intro text

    Example:
        >>> plan = "## My Plan\\n\\n- Step 1\\n- Step 2"
        >>> result = wrap_plan_in_metadata_block(plan)
        >>> "<details>" in result
        True
        >>> "This issue contains an implementation plan:" in result
        True
        >>> plan in result
        True
    """
    plan_content = plan.strip()

    # Build the wrapped format with proper spacing for GitHub markdown rendering
    # Blank lines around content inside <details> are required for proper rendering
    return f"""{intro_text}

<details>
<summary><code>erk-plan</code></summary>

{plan_content}

</details>"""


def extract_title_from_plan(plan: str) -> str:
    """Extract title from plan (H1 → H2 → first line fallback).

    Tries extraction in priority order:
    1. First H1 heading (# Title)
    2. First H2 heading (## Title)
    3. First non-empty line

    Title is cleaned of markdown formatting and whitespace.

    Args:
        plan: Plan content as markdown string

    Returns:
        Extracted title string, or "Implementation Plan" if extraction fails

    Example:
        >>> plan = "# Feature Name\\n\\nDetails..."
        >>> extract_title_from_plan(plan)
        'Feature Name'

        >>> plan = "## My Feature\\n\\nDetails..."
        >>> extract_title_from_plan(plan)
        'My Feature'

        >>> plan = "Some plain text\\n\\nMore text..."
        >>> extract_title_from_plan(plan)
        'Some plain text'
    """
    if not plan or not plan.strip():
        return "Implementation Plan"

    lines = plan.strip().split("\n")

    # Try H1 first
    for line in lines:
        line = line.strip()
        if line.startswith("# ") and len(line) > 2:
            # Remove # and clean
            title = line[2:].strip()
            # Remove markdown formatting
            title = re.sub(r"`([^`]+)`", r"\1", title)  # Remove backticks
            title = re.sub(r"\*\*([^*]+)\*\*", r"\1", title)  # Remove bold
            title = re.sub(r"\*([^*]+)\*", r"\1", title)  # Remove italic
            title = title.strip()
            if title:
                # Limit to 100 chars (GitHub recommendation)
                return title[:100] if len(title) > 100 else title

    # Try H2 second
    for line in lines:
        line = line.strip()
        if line.startswith("## ") and len(line) > 3:
            # Remove ## and clean
            title = line[3:].strip()
            # Remove markdown formatting
            title = re.sub(r"`([^`]+)`", r"\1", title)
            title = re.sub(r"\*\*([^*]+)\*\*", r"\1", title)
            title = re.sub(r"\*([^*]+)\*", r"\1", title)
            title = title.strip()
            if title:
                return title[:100] if len(title) > 100 else title

    # Fallback: first non-empty line
    for line in lines:
        line = line.strip()
        # Skip YAML front matter delimiters
        if line and line != "---":
            # Remove markdown formatting
            title = re.sub(r"`([^`]+)`", r"\1", line)
            title = re.sub(r"\*\*([^*]+)\*\*", r"\1", title)
            title = re.sub(r"\*([^*]+)\*", r"\1", title)
            title = title.strip()
            if title:
                return title[:100] if len(title) > 100 else title

    return "Implementation Plan"


def generate_filename_from_title(title: str) -> str:
    """Convert title to kebab-case filename with -plan.md suffix.

    Comprehensive transformation:
    1. Lowercase
    2. Replace spaces with hyphens
    3. Unicode normalization (NFD)
    4. Remove emojis and non-alphanumeric characters (except hyphens)
    5. Collapse consecutive hyphens
    6. Strip leading/trailing hyphens
    7. Validate at least one alphanumeric character remains
    8. Append "-plan.md"

    Returns "plan.md" if title is empty after cleanup.

    Args:
        title: Plan title to convert

    Returns:
        Sanitized filename ending with -plan.md

    Example:
        >>> generate_filename_from_title("User Auth Feature")
        'user-auth-feature-plan.md'

        >>> generate_filename_from_title("Fix: Bug #123")
        'fix-bug-123-plan.md'

        >>> generate_filename_from_title("🚀 Feature Launch 🎉")
        'feature-launch-plan.md'

        >>> generate_filename_from_title("café")
        'cafe-plan.md'
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
