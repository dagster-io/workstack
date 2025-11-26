"""Shared utilities for plan commands."""

from urllib.parse import urlparse


def parse_plan_identifier(identifier: str) -> int:
    """Parse issue number from numeric string or GitHub URL.

    Args:
        identifier: Issue number string (e.g., "42") or GitHub URL

    Returns:
        Issue number as integer

    Raises:
        ValueError: If identifier format is invalid
    """
    if identifier.isdigit():
        return int(identifier)

    # Security: Use proper URL parsing to validate hostname
    parsed = urlparse(identifier)
    if parsed.hostname == "github.com" and parsed.path:
        parts = parsed.path.rstrip("/").split("/")
        if len(parts) >= 2 and parts[-2] == "issues":
            if parts[-1].isdigit():
                return int(parts[-1])

    raise ValueError(f"Invalid identifier: {identifier}")
