"""Service for efficiently fetching plan list data via batched API calls."""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.github.abc import GitHub
from erk_shared.github.issues import GitHubIssues, IssueInfo
from erk_shared.github.types import PullRequestInfo, WorkflowRun


@dataclass(frozen=True)
class PlanListData:
    """Combined data for plan listing.

    Attributes:
        issues: List of IssueInfo objects with embedded comments
        issue_comments: Mapping of issue_number -> list of comment bodies
        pr_linkages: Mapping of issue_number -> list of PRs that close that issue
        workflow_runs: Mapping of display_title -> most relevant WorkflowRun
    """

    issues: list[IssueInfo]
    issue_comments: dict[int, list[str]]
    pr_linkages: dict[int, list[PullRequestInfo]]
    workflow_runs: dict[str, WorkflowRun | None]


class PlanListService:
    """Service for efficiently fetching plan list data.

    Composes GitHub and GitHubIssues integrations to batch fetch all data
    needed for plan listing.
    """

    def __init__(self, github: GitHub, github_issues: GitHubIssues) -> None:
        """Initialize PlanListService with required integrations.

        Args:
            github: GitHub integration for PR and workflow operations
            github_issues: GitHub issues integration for issue operations
        """
        self._github = github
        self._github_issues = github_issues

    def get_plan_list_data(
        self,
        repo_root: Path,
        labels: list[str],
        workflow_name: str,
        state: str | None = None,
        limit: int | None = None,
        skip_workflow_runs: bool = False,
    ) -> PlanListData:
        """Batch fetch all data needed for plan listing.

        Args:
            repo_root: Repository root directory
            labels: Labels to filter issues by (e.g., ["erk-plan"])
            workflow_name: Workflow filename for run lookup (e.g., "dispatch-erk-queue.yml")
            state: Filter by state ("open", "closed", or None for all)
            limit: Maximum number of issues to return (None for no limit)
            skip_workflow_runs: If True, skip fetching workflow runs (for performance)

        Returns:
            PlanListData containing issues, comments, PR linkages, and workflow runs
        """
        # Fetch issues using GitHubIssues integration
        issues = self._github_issues.list_issues(repo_root, labels=labels, state=state, limit=limit)

        # Extract issue numbers for batch operations
        issue_numbers = [issue.number for issue in issues]

        # Batch fetch comments for all issues
        issue_comments = self._github_issues.get_multiple_issue_comments(repo_root, issue_numbers)

        # Batch fetch PR linkages for all issues
        pr_linkages = self._github.get_prs_linked_to_issues(repo_root, issue_numbers)

        # Conditionally fetch workflow runs (skip for performance when not needed)
        if skip_workflow_runs:
            workflow_runs: dict[str, WorkflowRun | None] = {}
        else:
            # Extract issue titles for workflow run matching
            titles = [issue.title for issue in issues]
            workflow_runs = self._github.get_workflow_runs_by_titles(
                repo_root, workflow_name, titles
            )

        return PlanListData(
            issues=issues,
            issue_comments=issue_comments,
            pr_linkages=pr_linkages,
            workflow_runs=workflow_runs,
        )
