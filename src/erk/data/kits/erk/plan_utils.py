"""Pure functions for plan manipulation and metadata.

This module contains reusable pure functions for working with implementation plans.
These functions are used by both kit CLI commands and internal logic, providing
a single source of truth for plan operations.

All functions follow LBYL (Look Before You Leap) patterns and have no external
dependencies or I/O operations.
"""

import re


def wrap_plan_in_metadata_block(plan: str) -> str:
    """Return plan content for issue body.

    Returns plan content as-is (stripped). Metadata formatting and workflow
    instructions are now added via separate GitHub comments, not embedded
    in the issue body.

    This change allows the issue body to contain pure plan content while
    metadata blocks are added programmatically via comments.

    Args:
        plan: Raw plan content as markdown string

    Returns:
        Plan content stripped of leading/trailing whitespace

    Example:
        >>> plan = "## My Plan\\n\\n- Step 1\\n- Step 2"
        >>> result = wrap_plan_in_metadata_block(plan)
        >>> result == plan.strip()
        True
    """
    return plan.strip()


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
