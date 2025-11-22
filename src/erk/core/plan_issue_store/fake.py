"""In-memory fake implementation for plan issue storage."""

from pathlib import Path

from erk.core.plan_issue_store.store import PlanIssueStore
from erk.core.plan_issue_store.types import PlanIssue, PlanIssueQuery


class FakePlanIssueStore(PlanIssueStore):
    """In-memory fake implementation for testing.

    All state is provided via constructor. Supports filtering by state,
    labels (AND logic), and limit.
    """

    def __init__(self, plan_issues: dict[str, PlanIssue] | None = None) -> None:
        """Create FakePlanIssueStore with pre-configured state.

        Args:
            plan_issues: Mapping of plan_issue_identifier -> PlanIssue
        """
        self._plan_issues = plan_issues or {}

    def get_plan_issue(self, repo_root: Path, plan_issue_identifier: str) -> PlanIssue:
        """Get plan issue from fake storage.

        Args:
            repo_root: Repository root directory (ignored in fake)
            plan_issue_identifier: Issue identifier

        Returns:
            PlanIssue from fake storage

        Raises:
            RuntimeError: If plan issue identifier not found (simulates provider error)
        """
        if plan_issue_identifier not in self._plan_issues:
            msg = f"Plan issue '{plan_issue_identifier}' not found"
            raise RuntimeError(msg)
        return self._plan_issues[plan_issue_identifier]

    def list_plan_issues(self, repo_root: Path, query: PlanIssueQuery) -> list[PlanIssue]:
        """Query plan issues from fake storage.

        Args:
            repo_root: Repository root directory (ignored in fake)
            query: Filter criteria (labels, state, limit)

        Returns:
            List of PlanIssue matching the criteria
        """
        issues = list(self._plan_issues.values())

        # Filter by state
        if query.state:
            issues = [issue for issue in issues if issue.state == query.state]

        # Filter by labels (AND logic - all must match)
        if query.labels:
            issues = [
                issue for issue in issues if all(label in issue.labels for label in query.labels)
            ]

        # Apply limit
        if query.limit:
            issues = issues[: query.limit]

        return issues

    def get_provider_name(self) -> str:
        """Get the provider name.

        Returns:
            "fake"
        """
        return "fake"
