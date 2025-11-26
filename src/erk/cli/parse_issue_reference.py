"""Parse issue reference from user input."""

import re

import click
from erk_shared.output.output import user_output


def parse_issue_reference(reference: str) -> int:
    """Parse issue number from plain number or GitHub URL.

    Accepts:
      - Plain number: "123"
      - GitHub URL: "https://github.com/owner/repo/issues/123"

    Args:
        reference: Issue number or GitHub issue URL

    Returns:
        Issue number as positive integer

    Raises:
        SystemExit: If input format is invalid or number is not positive

    Examples:
        >>> parse_issue_reference("123")
        123
        >>> parse_issue_reference("https://github.com/owner/repo/issues/456")
        456
        >>> parse_issue_reference("https://github.com/owner/repo/issues/789#issuecomment-123")
        789
    """
    # Pattern matches the entire reference string:
    # - Start of string (^)
    # - Any characters before "issues/" (for GitHub URLs)
    # - Optional "issues/" prefix
    # - Digits (must be contiguous, no whitespace)
    # - Optional trailing slash
    # - Optional query string or fragment
    # - End of string ($)
    # Note: Uses \d+ which only matches digit sequences (no negative, no whitespace)
    pattern = r"^(?:.*issues/)?(\d+)(?:/)?(?:[?#].*)?$"
    match = re.match(pattern, reference)

    if match is None:
        user_output(
            click.style("Error: ", fg="red")
            + f"Invalid issue number or URL: {reference}\n\n"
            + "Expected formats:\n"
            + "  • Plain number: 123\n"
            + "  • GitHub URL: https://github.com/owner/repo/issues/456"
        )
        raise SystemExit(1)

    issue_number = int(match.group(1))

    # LBYL: Validate positive number before returning
    if issue_number <= 0:
        user_output(
            click.style("Error: ", fg="red")
            + f"Invalid issue number: {issue_number}\n\n"
            + "Issue number must be a positive integer"
        )
        raise SystemExit(1)

    return issue_number
