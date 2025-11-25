"""Service for efficiently fetching plan list data via batched API calls.

Schema Version 2 Optimization:
- Extracts last_dispatched_run_id directly from issue body metadata
- Uses direct workflow run lookup by ID (single API call per plan)
- Eliminates expensive get_workflow_runs_by_titles() which fetched 100+ runs
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.github.abc import GitHub
from erk_shared.github.issues import GitHubIssues, IssueInfo
from erk_shared.github.metadata import extract_plan_header_dispatch_info
from erk_shared.github.types import PullRequestInfo, WorkflowRun


@dataclass(frozen=True)
class PlanListData:
    """Combined data for plan listing.

    Attributes:
        issues: List of IssueInfo objects with embedded comments
        issue_comments: Mapping of issue_number -> list of comment bodies
        pr_linkages: Mapping of issue_number -> list of PRs that close that issue
        workflow_runs: Mapping of issue_number -> most relevant WorkflowRun (schema v2)
                       OR mapping of display_title -> WorkflowRun (schema v1 fallback)
    """

    issues: list[IssueInfo]
    issue_comments: dict[int, list[str]]
    pr_linkages: dict[int, list[PullRequestInfo]]
    workflow_runs: dict[str | int, WorkflowRun | None]


class PlanListService:
    """Service for efficiently fetching plan list data.

    Composes GitHub and GitHubIssues integrations to batch fetch all data
    needed for plan listing.

    Schema Version 2 Optimization:
    - New issues have last_dispatched_run_id in body metadata
    - Uses get_workflow_run(run_id) for direct lookup (O(n) API calls)
    - Falls back to title-based lookup for old-format issues
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

        Schema Version 2 Optimization:
        - Extracts last_dispatched_run_id from issue body (plan-header block)
        - Uses get_workflow_run(run_id) for direct lookup
        - Falls back to title-based lookup only for old-format issues

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
        workflow_runs: dict[str | int, WorkflowRun | None] = {}
        if not skip_workflow_runs:
            # Schema v2: Extract run_id from issue body and do direct lookups
            # Schema v1 fallback: Collect titles for title-based lookup
            v1_titles: list[str] = []

            for issue in issues:
                run_id, _ = extract_plan_header_dispatch_info(issue.body)
                if run_id is not None:
                    # Schema v2: Direct run lookup (efficient - single API call)
                    run = self._github.get_workflow_run(repo_root, run_id)
                    workflow_runs[issue.number] = run
                else:
                    # Schema v1: No run_id in body, will use title-based lookup
                    v1_titles.append(issue.title)

            # Fallback: Title-based lookup for old-format issues
            if v1_titles:
                title_runs = self._github.get_workflow_runs_by_titles(
                    repo_root, workflow_name, v1_titles
                )
                # Merge title-based results (keyed by title, not issue number)
                for title, run in title_runs.items():
                    workflow_runs[title] = run

        return PlanListData(
            issues=issues,
            issue_comments=issue_comments,
            pr_linkages=pr_linkages,
            workflow_runs=workflow_runs,
        )
