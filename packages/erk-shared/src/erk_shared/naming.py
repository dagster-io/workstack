"""Naming utilities for filenames and worktree names.

This module provides pure utility functions for transforming titles and names
into sanitized, filesystem-safe identifiers. All functions are pure (no I/O)
and follow LBYL patterns.
"""

import re
import unicodedata


def sanitize_worktree_name(name: str) -> str:
    """Sanitize a worktree name for use as a directory name.

    - Lowercases input
    - Replaces underscores with hyphens
    - Replaces characters outside `[A-Za-z0-9.-]` with `-`
    - Collapses consecutive `-`
    - Strips leading/trailing `-`
    - Truncates to 30 characters maximum (matches branch component sanitization)
    Returns `"work"` if the result is empty.

    The 30-character limit ensures worktree names match their corresponding branch
    names, maintaining consistency across the worktree/branch model.

    Args:
        name: Arbitrary string to sanitize

    Returns:
        Sanitized worktree name (max 30 chars)

    Examples:
        >>> sanitize_worktree_name("My_Feature")
        "my-feature"
        >>> sanitize_worktree_name("a" * 40)
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"  # 30 chars
    """
    lowered = name.strip().lower()
    # Replace underscores with hyphens
    replaced_underscores = lowered.replace("_", "-")
    # Replace unsafe characters with hyphens
    replaced = re.sub(r"[^a-z0-9.-]+", "-", replaced_underscores)
    # Collapse consecutive hyphens
    collapsed = re.sub(r"-+", "-", replaced)
    # Strip leading/trailing hyphens
    trimmed = collapsed.strip("-")
    result = trimmed or "work"

    # Truncate to 30 characters and strip trailing hyphens
    if len(result) > 30:
        result = result[:30].rstrip("-")

    return result


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
