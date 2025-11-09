"""Fake GitHub operations for testing.

FakeGitHubOps is an in-memory implementation that accepts pre-configured state
in its constructor. Construct instances directly with keyword arguments.
"""

from pathlib import Path

from workstack.core.github_ops import GitHubOps, PRInfo, PullRequestInfo


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
    ) -> None:
        """Create FakeGitHubOps with pre-configured state.

        Args:
            prs: Mapping of branch name -> PullRequestInfo
            pr_statuses: Legacy parameter for backward compatibility.
                        Mapping of branch name -> (state, pr_number, title)
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
            return PRInfo(state, pr_number, title)

        pr = self._prs.get(branch)
        if pr is None:
            return PRInfo("NONE", None, None)
        # PullRequestInfo has: number, state, url, is_draft, checks_passing
        # But get_pr_status expects: state, number, title
        # Using url as title since PullRequestInfo doesn't have a title field
        return PRInfo(pr.state, pr.number, pr.url)
