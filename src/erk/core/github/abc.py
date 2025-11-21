"""Abstract base class for GitHub operations."""

from abc import ABC, abstractmethod
from pathlib import Path

from erk.core.github.types import PRInfo, PRMergeability, PullRequestInfo


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
    ) -> None:
        """Trigger a GitHub Actions workflow via gh CLI.

        Args:
            repo_root: Repository root directory
            workflow: Workflow filename (e.g., "implement-plan.yml")
            inputs: Workflow inputs as key-value pairs
            ref: Branch or tag to run workflow from (default: repository default branch)
        """
        ...
