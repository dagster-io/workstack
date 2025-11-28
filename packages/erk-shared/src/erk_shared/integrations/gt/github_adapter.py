"""Adapter that implements GitHubGtKit by wrapping GitHub ABC.

This adapter enables dependency injection of the main GitHub interface into
GtKit implementations, allowing shared FakeGitHub instances across test contexts.
"""

from pathlib import Path

from erk_shared.github.abc import GitHub
from erk_shared.integrations.gt.abc import GitGtKit, GitHubGtKit


class GitHubAdapter(GitHubGtKit):
    """Adapts GitHub ABC to GitHubGtKit interface using git context.

    This adapter resolves the repository root and current branch from the
    GitGtKit interface, then delegates to the injected GitHub implementation.

    This enables:
    - Proper dependency injection for GtKit implementations
    - Sharing FakeGitHub across erk core and GT kit test contexts
    - Single source of truth for GitHub operations
    """

    def __init__(self, github: GitHub, git: GitGtKit) -> None:
        """Initialize adapter with GitHub and Git implementations.

        Args:
            github: The GitHub ABC implementation to delegate to
            git: The Git implementation for resolving repo context
        """
        self._github = github
        self._git = git

    def _get_repo_root(self) -> Path:
        """Get repository root path from git context."""
        return Path(self._git.get_repository_root())

    def _get_current_branch(self) -> str | None:
        """Get current branch name from git context."""
        return self._git.get_current_branch()

    def _get_current_pr_number(self) -> int | None:
        """Get PR number for current branch, if any."""
        branch = self._get_current_branch()
        if branch is None:
            return None
        pr_info = self._github.get_pr_status(self._get_repo_root(), branch, debug=False)
        return pr_info.pr_number

    def get_pr_info(self) -> tuple[int, str] | None:
        """Get PR number and URL for current branch."""
        branch = self._get_current_branch()
        if branch is None:
            return None

        repo_root = self._get_repo_root()
        pr_info = self._github.get_pr_status(repo_root, branch, debug=False)

        if pr_info.pr_number is None:
            return None

        # Construct URL from PR info
        # We need to get the actual URL - use get_prs_for_repo to find it
        prs = self._github.get_prs_for_repo(repo_root, include_checks=False)
        if branch in prs:
            return (prs[branch].number, prs[branch].url)

        # Fallback: construct a generic URL
        return (pr_info.pr_number, f"https://github.com/owner/repo/pull/{pr_info.pr_number}")

    def get_pr_state(self) -> tuple[int, str] | None:
        """Get PR number and state for current branch."""
        branch = self._get_current_branch()
        if branch is None:
            return None

        repo_root = self._get_repo_root()
        pr_info = self._github.get_pr_status(repo_root, branch, debug=False)

        if pr_info.pr_number is None:
            return None

        return (pr_info.pr_number, pr_info.state)

    def update_pr_metadata(self, title: str, body: str) -> bool:
        """Update PR title and body for current branch."""
        pr_number = self._get_current_pr_number()
        if pr_number is None:
            return False

        return self._github.update_pr_metadata(self._get_repo_root(), pr_number, title, body)

    def mark_pr_ready(self) -> bool:
        """Mark PR as ready for review."""
        pr_number = self._get_current_pr_number()
        if pr_number is None:
            return False

        return self._github.mark_pr_ready(self._get_repo_root(), pr_number)

    def merge_pr(self) -> bool:
        """Merge the PR for current branch using squash merge."""
        pr_number = self._get_current_pr_number()
        if pr_number is None:
            return False

        try:
            self._github.merge_pr(self._get_repo_root(), pr_number, squash=True)
            return True
        except RuntimeError:
            return False

    def get_graphite_pr_url(self, pr_number: int) -> str | None:
        """Get Graphite PR URL for given PR number."""
        return self._github.get_graphite_pr_url(self._get_repo_root(), pr_number)

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Check GitHub CLI authentication status."""
        return self._github.check_auth_status()

    def get_pr_diff(self, pr_number: int) -> str:
        """Get the diff for a PR."""
        return self._github.get_pr_diff(self._get_repo_root(), pr_number)

    def get_pr_status(self, branch: str) -> tuple[int | None, str | None]:
        """Get PR number and URL for a specific branch."""
        repo_root = self._get_repo_root()
        prs = self._github.get_prs_for_repo(repo_root, include_checks=False)

        if branch in prs:
            pr = prs[branch]
            return (pr.number, pr.url)

        return (None, None)

    def get_pr_mergeability(self, pr_number: int) -> tuple[str, str]:
        """Get PR mergeability status from GitHub API."""
        result = self._github.get_pr_mergeability(self._get_repo_root(), pr_number)

        if result is None:
            return ("UNKNOWN", "UNKNOWN")

        return (result.mergeable, result.merge_state_status)
