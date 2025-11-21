"""No-op wrapper for GitHub operations."""

from pathlib import Path

from erk.core.github.abc import GitHub
from erk.core.github.types import PRInfo, PRMergeability, PullRequestInfo


class NoopGitHub(GitHub):
    """No-op wrapper for GitHub operations.

    Read operations are delegated to the wrapped implementation.
    Write operations return without executing (no-op behavior).

    This wrapper prevents destructive GitHub operations from executing in dry-run mode,
    while still allowing read operations for validation.
    """

    def __init__(self, wrapped: GitHub) -> None:
        """Initialize dry-run wrapper with a real implementation.

        Args:
            wrapped: The real GitHub operations implementation to wrap
        """
        self._wrapped = wrapped

    def get_prs_for_repo(
        self, repo_root: Path, *, include_checks: bool
    ) -> dict[str, PullRequestInfo]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_prs_for_repo(repo_root, include_checks=include_checks)

    def get_pr_status(self, repo_root: Path, branch: str, *, debug: bool) -> PRInfo:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_pr_status(repo_root, branch, debug=debug)

    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str | None:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_pr_base_branch(repo_root, pr_number)

    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """No-op for updating PR base branch in dry-run mode."""
        # Do nothing - prevents actual PR base update
        pass

    def get_pr_mergeability(self, repo_root: Path, pr_number: int) -> PRMergeability | None:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_pr_mergeability(repo_root, pr_number)

    def enrich_prs_with_ci_status_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.enrich_prs_with_ci_status_batch(prs, repo_root)

    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
    ) -> None:
        """No-op for merging PR in dry-run mode."""
        # Do nothing - prevents actual PR merge
        pass

    def trigger_workflow(
        self,
        repo_root: Path,
        workflow: str,
        inputs: dict[str, str],
        ref: str | None = None,
    ) -> str:
        """No-op for triggering workflow in dry-run mode.

        Returns:
            A fake run ID for dry-run mode
        """
        # Return fake run ID - prevents actual workflow trigger
        return "noop-run-12345"
