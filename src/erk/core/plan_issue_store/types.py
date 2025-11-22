"""Core types for provider-agnostic plan issue storage."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PlanIssueState(Enum):
    """State of a plan issue."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class PlanIssue:
    """Provider-agnostic representation of a plan issue.

    Fields:
        plan_issue_identifier: Provider-specific ID as string
            (GitHub: "42", Jira: "PROJ-123", Linear: UUID)
        title: Issue title
        body: Issue body/description
        state: Issue state (OPEN or CLOSED)
        url: Web URL to view the issue
        labels: List of label names
        assignees: List of assignee usernames
        created_at: Creation timestamp
        updated_at: Last update timestamp
        metadata: Provider-specific fields (e.g., {"number": 42} for GitHub)
    """

    plan_issue_identifier: str
    title: str
    body: str
    state: PlanIssueState
    url: str
    labels: list[str]
    assignees: list[str]
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, object]


@dataclass(frozen=True)
class PlanIssueQuery:
    """Query parameters for filtering plan issues.

    Fields:
        labels: Filter by labels (all must match - AND logic)
        state: Filter by state (OPEN, CLOSED, or None for all)
        limit: Maximum number of results to return
    """

    labels: list[str] | None = None
    state: PlanIssueState | None = None
    limit: int | None = None
