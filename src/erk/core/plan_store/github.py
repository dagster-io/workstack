"""GitHub implementation of plan storage."""

from datetime import UTC
from pathlib import Path

from erk_shared.github.issues import GitHubIssues, IssueInfo

from erk.core.plan_store.store import PlanStore
from erk.core.plan_store.types import Plan, PlanQuery, PlanState


class GitHubPlanStore(PlanStore):
    """GitHub implementation using gh CLI.

    Wraps GitHub issue operations and converts to provider-agnostic Plan format.
    """

    def __init__(self, github_issues: GitHubIssues):
        """Initialize GitHubPlanStore with GitHub issues interface.

        Args:
            github_issues: GitHubIssues implementation to use for issue operations
        """
        self._github_issues = github_issues

    def get_plan(self, repo_root: Path, plan_identifier: str) -> Plan:
        """Fetch plan from GitHub by identifier.

        Args:
            repo_root: Repository root directory
            plan_identifier: Issue number as string (e.g., "42")

        Returns:
            Plan with converted data

        Raises:
            RuntimeError: If gh CLI fails or plan not found
        """
        issue_number = int(plan_identifier)
        issue_info = self._github_issues.get_issue(repo_root, issue_number)
        return self._convert_to_plan(issue_info)

    def list_plans(self, repo_root: Path, query: PlanQuery) -> list[Plan]:
        """Query plans from GitHub.

        Args:
            repo_root: Repository root directory
            query: Filter criteria (labels, state, limit)

        Returns:
            List of Plan matching the criteria

        Raises:
            RuntimeError: If gh CLI fails
        """
        # Map PlanState to GitHub state string
        state_str = None
        if query.state == PlanState.OPEN:
            state_str = "open"
        elif query.state == PlanState.CLOSED:
            state_str = "closed"

        # Use GitHubIssues native limit support for efficient querying
        issues = self._github_issues.list_issues(
            repo_root,
            labels=query.labels,
            state=state_str,
            limit=query.limit,
        )

        return [self._convert_to_plan(issue) for issue in issues]

    def get_provider_name(self) -> str:
        """Get the provider name.

        Returns:
            "github"
        """
        return "github"

    def _convert_to_plan(self, issue_info: IssueInfo) -> Plan:
        """Convert IssueInfo to Plan.

        Args:
            issue_info: IssueInfo from GitHubIssues interface

        Returns:
            Plan with normalized data
        """
        # Normalize state
        state = PlanState.OPEN if issue_info.state == "OPEN" else PlanState.CLOSED

        # Store GitHub-specific number in metadata for future operations
        metadata: dict[str, object] = {"number": issue_info.number}

        return Plan(
            plan_identifier=str(issue_info.number),
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
