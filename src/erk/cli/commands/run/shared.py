"""Shared utilities for run commands."""


def extract_issue_number(display_title: str | None) -> int | None:
    """Extract issue number from display_title format '123:abc456'.

    Handles:
    - New format: "123:abc456" → 123
    - Old format: "Issue title [abc123]" → None (no colon at start)
    - None or empty → None
    """
    if not display_title or ":" not in display_title:
        return None
    parts = display_title.split(":", 1)
    # Validate that the first part is a number
    first_part = parts[0].strip()
    if not first_part.isdigit():
        return None
    return int(first_part)
