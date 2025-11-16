"""Fake GitHub operations for testing.

FakeGitHubOps is an in-memory implementation that accepts pre-configured state
in its constructor. Construct instances directly with keyword arguments.
"""

from pathlib import Path
from typing import cast

from workstack.core.github_ops import GitHubOps, PRInfo, PRMergeability, PRState, PullRequestInfo


class FakeGitHubOps(GitHubOps):
    """In-memory fake implementation of GitHub operations.

    This class has NO public setup methods. All state is provided via constructor
    using keyword arguments with sensible defaults (empty dicts).
    """

    def __init__(
        self,
        *,
        prs: dict[str, PullRequestInfo] | None = None,
        pr_statuses: dict[str, tuple[str | None, int | None, str | None]] | None = None,
        pr_bases: dict[int, str] | None = None,
        pr_mergeability: dict[int, PRMergeability | None] | None = None,
    ) -> None:
        """Create FakeGitHubOps with pre-configured state.

        Args:
            prs: Mapping of branch name -> PullRequestInfo
            pr_statuses: Legacy parameter for backward compatibility.
                        Mapping of branch name -> (state, pr_number, title)
            pr_bases: Mapping of pr_number -> base_branch
            pr_mergeability: Mapping of pr_number -> PRMergeability (None for API errors)
        """
        if prs is not None and pr_statuses is not None:
            msg = "Cannot specify both prs and pr_statuses"
            raise ValueError(msg)

        if pr_statuses is not None:
            # Convert legacy pr_statuses format to PullRequestInfo
            self._prs = {}
            self._pr_statuses = pr_statuses
        else:
            self._prs = prs or {}
            self._pr_statuses = None

        self._pr_bases = pr_bases or {}
        self._pr_mergeability = pr_mergeability or {}
        self._updated_pr_bases: list[tuple[int, str]] = []
        self._merged_prs: list[int] = []

    @property
    def merged_prs(self) -> list[int]:
        """List of PR numbers that were merged."""
        return self._merged_prs

    def get_prs_for_repo(
        self, repo_root: Path, *, include_checks: bool
    ) -> dict[str, PullRequestInfo]:
        """Get PR information for all branches (returns pre-configured data).

        The include_checks parameter is accepted but ignored - fake returns the
        same pre-configured data regardless of this parameter.
        """
        return self._prs

    def get_pr_status(self, repo_root: Path, branch: str, *, debug: bool) -> PRInfo:
        """Get PR status from configured PRs.

        Returns PRInfo("NONE", None, None) if branch not found.
        Note: Returns URL in place of title since PullRequestInfo has no title field.
        """
        # Support legacy pr_statuses format
        if self._pr_statuses is not None:
            result = self._pr_statuses.get(branch)
            if result is None:
                return PRInfo("NONE", None, None)
            state, pr_number, title = result
            # Convert None state to "NONE" for consistency
            if state is None:
                state = "NONE"
            return PRInfo(cast(PRState, state), pr_number, title)

        pr = self._prs.get(branch)
        if pr is None:
            return PRInfo("NONE", None, None)
        # PullRequestInfo has: number, state, url, is_draft, checks_passing
        # But get_pr_status expects: state, number, title
        # Using url as title since PullRequestInfo doesn't have a title field
        return PRInfo(cast(PRState, pr.state), pr.number, pr.url)

    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str | None:
        """Get current base branch of a PR from configured state.

        Returns None if PR number not found.
        """
        return self._pr_bases.get(pr_number)

    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """Record PR base branch update in mutation tracking list."""
        self._updated_pr_bases.append((pr_number, new_base))

    def get_pr_mergeability(self, repo_root: Path, pr_number: int) -> PRMergeability | None:
        """Get PR mergeability status from configured state.

        Returns configured mergeability or defaults to MERGEABLE if not configured.
        """
        if pr_number in self._pr_mergeability:
            return self._pr_mergeability[pr_number]
        # Default to MERGEABLE if not configured
        return PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN")

    def enrich_prs_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Enrich PRs with CI status and mergeability using batched query.

        In the fake implementation, we assume PRs already have CI status and mergeability if configured.
        This method is a no-op that returns the input unchanged.
        """
        return prs

    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
    ) -> None:
        """Record PR merge in mutation tracking list."""
        self._merged_prs.append(pr_number)

    @property
    def updated_pr_bases(self) -> list[tuple[int, str]]:
        """Read-only access to tracked PR base updates for test assertions."""
        return self._updated_pr_bases
