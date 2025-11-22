"""GitHub implementation of plan issue storage."""

from datetime import UTC
from pathlib import Path

from erk.core.github.issues import GitHubIssues, IssueInfo
from erk.core.plan_issue_store.store import PlanIssueStore
from erk.core.plan_issue_store.types import PlanIssue, PlanIssueQuery, PlanIssueState


class GitHubPlanIssueStore(PlanIssueStore):
    """GitHub implementation using gh CLI.

    Wraps GitHub issue operations and converts to provider-agnostic PlanIssue format.
    """

    def __init__(self, github_issues: GitHubIssues):
        """Initialize GitHubPlanIssueStore with GitHub issues interface.

        Args:
            github_issues: GitHubIssues implementation to use for issue operations
        """
        self._github_issues = github_issues

    def get_plan_issue(self, repo_root: Path, plan_issue_identifier: str) -> PlanIssue:
        """Fetch plan issue from GitHub by identifier.

        Args:
            repo_root: Repository root directory
            plan_issue_identifier: Issue number as string (e.g., "42")

        Returns:
            PlanIssue with converted data

        Raises:
            RuntimeError: If gh CLI fails or issue not found
        """
        issue_number = int(plan_issue_identifier)
        issue_info = self._github_issues.get_issue(repo_root, issue_number)
        return self._convert_to_plan_issue(issue_info)

    def list_plan_issues(self, repo_root: Path, query: PlanIssueQuery) -> list[PlanIssue]:
        """Query plan issues from GitHub.

        Args:
            repo_root: Repository root directory
            query: Filter criteria (labels, state, limit)

        Returns:
            List of PlanIssue matching the criteria

        Raises:
            RuntimeError: If gh CLI fails
        """
        # Map PlanIssueState to GitHub state string
        state_str = None
        if query.state == PlanIssueState.OPEN:
            state_str = "open"
        elif query.state == PlanIssueState.CLOSED:
            state_str = "closed"

        # Call GitHubIssues.list_issues with appropriate filters
        # Note: GitHubIssues doesn't support limit, so we'll slice the results
        issues = self._github_issues.list_issues(repo_root, labels=query.labels, state=state_str)

        # Apply limit if specified
        if query.limit:
            issues = issues[: query.limit]

        return [self._convert_to_plan_issue(issue) for issue in issues]

    def get_provider_name(self) -> str:
        """Get the provider name.

        Returns:
            "github"
        """
        return "github"

    def _convert_to_plan_issue(self, issue_info: IssueInfo) -> PlanIssue:
        """Convert IssueInfo to PlanIssue.

        Args:
            issue_info: IssueInfo from GitHubIssues interface

        Returns:
            PlanIssue with normalized data
        """
        # Normalize state
        state = PlanIssueState.OPEN if issue_info.state == "OPEN" else PlanIssueState.CLOSED

        # Store GitHub-specific number in metadata for future operations
        metadata: dict[str, object] = {"number": issue_info.number}

        return PlanIssue(
            plan_issue_identifier=str(issue_info.number),
            title=issue_info.title,
            body=issue_info.body,
            state=state,
            url=issue_info.url,
            labels=issue_info.labels,
            assignees=issue_info.assignees,
            created_at=issue_info.created_at.astimezone(UTC),
            updated_at=issue_info.updated_at.astimezone(UTC),
            metadata=metadata,
        )
