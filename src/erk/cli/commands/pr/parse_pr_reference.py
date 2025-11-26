"""Parse PR reference from user input."""

import re

import click
from erk_shared.output.output import user_output


def parse_pr_reference(reference: str) -> int:
    """Parse PR number from plain number or GitHub URL.

    Accepts:
      - Plain number: "123"
      - GitHub URL: "https://github.com/owner/repo/pull/123"

    Args:
        reference: PR number or GitHub pull request URL

    Returns:
        PR number as integer

    Raises:
        SystemExit: If input format is invalid

    Examples:
        >>> parse_pr_reference("123")
        123
        >>> parse_pr_reference("https://github.com/owner/repo/pull/456")
        456
        >>> parse_pr_reference("https://github.com/owner/repo/pull/789#issuecomment-123")
        789
    """
    # Pattern matches:
    # - Optional "pull/" prefix
    # - Digits
    # - Optional query string or fragment
    pattern = r"(?:pull/)?(\d+)(?:[?#].*)?$"
    match = re.search(pattern, reference)

    if match is None:
        user_output(
            click.style("Error: ", fg="red")
            + f"Invalid PR number or URL: {reference}\n\n"
            + "Expected formats:\n"
            + "  • Plain number: 123\n"
            + "  • GitHub URL: https://github.com/owner/repo/pull/456"
        )
        raise SystemExit(1)

    return int(match.group(1))
