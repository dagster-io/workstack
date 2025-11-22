"""GitHub implementation of plan issue storage."""

import json
from datetime import UTC, datetime
from pathlib import Path

from erk.core.github.parsing import execute_gh_command
from erk.core.plan_issue_store.store import PlanIssueStore
from erk.core.plan_issue_store.types import PlanIssue, PlanIssueQuery, PlanIssueState


class GitHubPlanIssueStore(PlanIssueStore):
    """GitHub implementation using gh CLI.

    Wraps GitHub issue operations and converts to provider-agnostic PlanIssue format.
    """

    def __init__(self, execute_fn=None):
        """Initialize GitHubPlanIssueStore with optional command executor.

        Args:
            execute_fn: Optional function to execute commands (for testing).
                       If None, uses execute_gh_command.
        """
        self._execute = execute_fn or execute_gh_command

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
        cmd = [
            "gh",
            "issue",
            "view",
            plan_issue_identifier,
            "--json",
            "number,title,body,state,url,labels,assignees,createdAt,updatedAt",
        ]
        stdout = self._execute(cmd, repo_root)
        data = json.loads(stdout)

        return self._convert_to_plan_issue(data)

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
        cmd = [
            "gh",
            "issue",
            "list",
            "--json",
            "number,title,body,state,url,labels,assignees,createdAt,updatedAt",
        ]

        # Add label filters (AND logic - all must match)
        if query.labels:
            for label in query.labels:
                cmd.extend(["--label", label])

        # Add state filter
        if query.state:
            state_str = "open" if query.state == PlanIssueState.OPEN else "closed"
            cmd.extend(["--state", state_str])

        # Add limit
        if query.limit:
            cmd.extend(["--limit", str(query.limit)])

        stdout = self._execute(cmd, repo_root)
        data = json.loads(stdout)

        return [self._convert_to_plan_issue(issue) for issue in data]

    def get_provider_name(self) -> str:
        """Get the provider name.

        Returns:
            "github"
        """
        return "github"

    def _convert_to_plan_issue(self, github_data: dict) -> PlanIssue:
        """Convert GitHub issue JSON to PlanIssue.

        Args:
            github_data: GitHub issue data from gh CLI

        Returns:
            PlanIssue with normalized data
        """
        # Parse timestamps (ISO8601 with 'Z' suffix)
        created_at = self._parse_timestamp(github_data["createdAt"])
        updated_at = self._parse_timestamp(github_data["updatedAt"])

        # Extract label names from label objects
        labels = [label["name"] for label in github_data.get("labels", [])]

        # Extract assignee logins
        assignees = [assignee["login"] for assignee in github_data.get("assignees", [])]

        # Normalize state
        state_str = github_data["state"]
        state = PlanIssueState.OPEN if state_str == "OPEN" else PlanIssueState.CLOSED

        # Store GitHub-specific number in metadata for future operations
        metadata = {"number": github_data["number"]}

        return PlanIssue(
            plan_issue_identifier=str(github_data["number"]),
            title=github_data["title"],
            body=github_data.get("body", ""),
            state=state,
            url=github_data["url"],
            labels=labels,
            assignees=assignees,
            created_at=created_at,
            updated_at=updated_at,
            metadata=metadata,
        )

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse ISO8601 timestamp with 'Z' suffix to datetime.

        Args:
            timestamp_str: ISO8601 timestamp string (e.g., "2024-01-15T10:30:00Z")

        Returns:
            datetime object with UTC timezone
        """
        # GitHub returns timestamps with 'Z' suffix (UTC)
        # Replace 'Z' with '+00:00' for parsing
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1] + "+00:00"

        return datetime.fromisoformat(timestamp_str).astimezone(UTC)
