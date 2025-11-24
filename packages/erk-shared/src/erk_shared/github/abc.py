"""Abstract base class for GitHub operations."""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.github.types import PRInfo, PRMergeability, PullRequestInfo, WorkflowRun


class GitHub(ABC):
    """Abstract interface for GitHub operations.

    All implementations (real and fake) must implement this interface.
    """

    @abstractmethod
    def get_prs_for_repo(
        self, repo_root: Path, *, include_checks: bool
    ) -> dict[str, PullRequestInfo]:
        """Get PR information for all branches in the repository.

        Args:
            repo_root: Repository root directory
            include_checks: If True, fetch CI check status (slower). If False, skip check status

        Returns:
            Mapping of branch name -> PullRequestInfo
            - checks_passing is None when include_checks=False
            Empty dict if gh CLI is not available or not authenticated
        """
        ...

    @abstractmethod
    def get_pr_status(self, repo_root: Path, branch: str, *, debug: bool) -> PRInfo:
        """Get PR status for a specific branch.

        Args:
            repo_root: Repository root directory
            branch: Branch name to check
            debug: If True, print debug information

        Returns:
            PRInfo with state, pr_number, and title
            - state: "OPEN", "MERGED", "CLOSED", or "NONE" if no PR exists
            - pr_number: PR number or None if no PR exists
            - title: PR title or None if no PR exists
        """
        ...

    @abstractmethod
    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str | None:
        """Get current base branch of a PR from GitHub.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to query

        Returns:
            Name of the base branch, or None if query fails
        """
        ...

    @abstractmethod
    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """Update base branch of a PR on GitHub.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to update
            new_base: New base branch name
        """
        ...

    @abstractmethod
    def get_pr_mergeability(self, repo_root: Path, pr_number: int) -> PRMergeability | None:
        """Get PR mergeability status from GitHub.

        Returns None if PR not found or API error.
        """
        ...

    @abstractmethod
    def fetch_pr_titles_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Fetch PR titles for all PRs in a single batched GraphQL query.

        This is a lighter-weight alternative to enrich_prs_with_ci_status_batch
        that only fetches titles, not CI status or mergeability.

        Args:
            prs: Mapping of branch name to PullRequestInfo (without titles)
            repo_root: Repository root directory

        Returns:
            Mapping of branch name to PullRequestInfo (with titles enriched)
        """
        ...

    @abstractmethod
    def enrich_prs_with_ci_status_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Enrich PR information with CI check status and mergeability using batched GraphQL query.

        Fetches both CI status and mergeability for all PRs in a single GraphQL API call,
        dramatically improving performance over serial fetching.

        Args:
            prs: Mapping of branch name to PullRequestInfo (without CI status or mergeability)
            repo_root: Repository root directory

        Returns:
            Mapping of branch name to PullRequestInfo (with CI status and has_conflicts enriched)
        """
        ...

    @abstractmethod
    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
    ) -> None:
        """Merge a pull request on GitHub.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to merge
            squash: If True, use squash merge strategy (default: True)
            verbose: If True, show detailed output
        """
        ...

    @abstractmethod
    def trigger_workflow(
        self,
        repo_root: Path,
        workflow: str,
        inputs: dict[str, str],
        ref: str | None = None,
    ) -> str:
        """Trigger a GitHub Actions workflow via gh CLI.

        Args:
            repo_root: Repository root directory
            workflow: Workflow filename (e.g., "implement-plan.yml")
            inputs: Workflow inputs as key-value pairs
            ref: Branch or tag to run workflow from (default: repository default branch)

        Returns:
            The GitHub Actions run ID as a string
        """
        ...

    @abstractmethod
    def create_pr(
        self,
        repo_root: Path,
        branch: str,
        title: str,
        body: str,
        base: str | None = None,
    ) -> int:
        """Create a pull request.

        Args:
            repo_root: Repository root directory
            branch: Source branch for the PR
            title: PR title
            body: PR body (markdown)
            base: Target base branch (defaults to trunk branch if None)

        Returns:
            PR number
        """
        ...

    @abstractmethod
    def list_workflow_runs(
        self, repo_root: Path, workflow: str, limit: int = 50
    ) -> list[WorkflowRun]:
        """List workflow runs for a specific workflow.

        Args:
            repo_root: Repository root directory
            workflow: Workflow filename (e.g., "implement-plan.yml")
            limit: Maximum number of runs to return (default: 50)

        Returns:
            List of workflow runs, ordered by creation time (newest first)
        """
        ...

    @abstractmethod
    def get_workflow_run(self, repo_root: Path, run_id: str) -> WorkflowRun | None:
        """Get details for a specific workflow run by ID.

        Args:
            repo_root: Repository root directory
            run_id: GitHub Actions run ID

        Returns:
            WorkflowRun with status and conclusion, or None if not found
        """
        ...

    @abstractmethod
    def get_run_logs(self, repo_root: Path, run_id: str) -> str:
        """Get logs for a workflow run.

        Args:
            repo_root: Repository root directory
            run_id: GitHub Actions run ID

        Returns:
            Log text as string

        Raises:
            RuntimeError: If gh CLI command fails
        """
        ...

    @abstractmethod
    def get_prs_linked_to_issues(
        self, repo_root: Path, issue_numbers: list[int]
    ) -> dict[int, list[PullRequestInfo]]:
        """Get PRs linked to issues via closing keywords.

        Queries GitHub for all PRs that link to the given issues using
        closing keywords (Closes, Fixes, Resolves). Returns a mapping
        of issue numbers to the PRs that close them.

        Args:
            repo_root: Repository root directory
            issue_numbers: List of issue numbers to query

        Returns:
            Mapping of issue_number -> list of PRs that close that issue.
            PRs are sorted by created_at descending (most recent first).
            Returns empty dict if no PRs link to any of the issues.
        """
        ...

    @abstractmethod
    def get_workflow_runs_by_branches(
        self, repo_root: Path, workflow: str, branches: list[str]
    ) -> dict[str, WorkflowRun | None]:
        """Get most relevant workflow runs for specific branches.

        For each branch, returns the most relevant run based on priority:
        1. In-progress or queued runs (highest priority)
        2. Failed runs
        3. Most recent completed run

        Args:
            repo_root: Repository root directory
            workflow: Workflow filename (e.g., "dispatch-erk-queue.yml")
            branches: List of branch names to query

        Returns:
            Mapping of branch name -> WorkflowRun (or None if no runs found).
            Only includes branches that have workflow runs.
        """
        ...
