"""Test utilities for GitHub issue operations."""

from datetime import UTC, datetime

from erk.core.github.issues import IssueInfo


def create_test_issue(
    number: int,
    title: str = "Test Issue",
    body: str = "",
    state: str = "OPEN",
    url: str | None = None,
) -> IssueInfo:
    """Factory for creating IssueInfo instances in tests with sensible defaults.

    Args:
        number: Issue number
        title: Issue title (defaults to "Test Issue")
        body: Issue body (defaults to empty string)
        state: Issue state (defaults to "OPEN")
        url: Issue URL (defaults to auto-generated GitHub URL)

    Returns:
        IssueInfo instance with provided or default values
    """
    if url is None:
        url = f"https://github.com/owner/repo/issues/{number}"
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state=state,
        url=url,
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
