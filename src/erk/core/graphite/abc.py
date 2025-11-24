"""Abstract base class for Graphite operations."""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.git.abc import Git
from erk_shared.github.types import PullRequestInfo

from erk.core.branch_metadata import BranchMetadata


class Graphite(ABC):
    """Abstract interface for Graphite operations.

    All implementations (real and fake) must implement this interface.
    """

    @abstractmethod
    def get_graphite_url(self, owner: str, repo: str, pr_number: int) -> str:
        """Get Graphite PR URL for a pull request.

        Args:
            owner: GitHub repository owner (e.g., "dagster-io")
            repo: GitHub repository name (e.g., "erk")
            pr_number: GitHub PR number

        Returns:
            Graphite PR URL (e.g., "https://app.graphite.com/github/pr/dagster-io/erk/23")
        """
        ...

    @abstractmethod
    def sync(self, repo_root: Path, *, force: bool, quiet: bool) -> None:
        """Run gt sync to synchronize with remote.

        Args:
            repo_root: Repository root directory
            force: If True, pass --force flag to gt sync
            quiet: If True, pass --quiet flag to gt sync for minimal output
        """
        ...

    @abstractmethod
    def restack(self, repo_root: Path, *, no_interactive: bool, quiet: bool) -> None:
        """Run gt restack to rebase the current stack.

        This is more surgical than sync - it only affects the current stack,
        not all branches in the repository. Safe to use in non-interactive
        mode during automated workflows.

        Args:
            repo_root: Repository root directory
            no_interactive: If True, pass --no-interactive flag to prevent prompts
            quiet: If True, pass --quiet flag to gt restack for minimal output
        """
        ...

    @abstractmethod
    def get_prs_from_graphite(self, git_ops: Git, repo_root: Path) -> dict[str, PullRequestInfo]:
        """Get PR information from Graphite's local cache.

        Reads .git/.graphite_pr_info and returns PR data in the same format
        as GitHub.get_prs_for_repo() for compatibility.

        Args:
            git_ops: Git instance for accessing git common directory
            repo_root: Repository root directory

        Returns:
            Mapping of branch name -> PullRequestInfo
            - checks_passing is always None (CI status not available)
            - Empty dict if .graphite_pr_info doesn't exist
        """
        ...

    @abstractmethod
    def get_all_branches(self, git_ops: Git, repo_root: Path) -> dict[str, BranchMetadata]:
        """Get all gt-tracked branches with metadata.

        Reads .git/.graphite_cache_persist and returns branch relationship data
        along with current commit SHAs from git.

        Args:
            git_ops: Git instance for accessing git common directory and branch heads
            repo_root: Repository root directory

        Returns:
            Mapping of branch name -> BranchMetadata
            Empty dict if:
            - .graphite_cache_persist doesn't exist
            - Git common directory cannot be determined
        """
        ...

    @abstractmethod
    def get_branch_stack(self, git_ops: Git, repo_root: Path, branch: str) -> list[str] | None:
        """Get the linear graphite stack for a given branch.

        This function builds the linear chain of branches that the given branch belongs to.
        The chain includes:
        - All ancestor branches from current down to trunk
        - All descendant branches from current up to the leaf

        Args:
            git_ops: Git instance for accessing git common directory and branch heads
            repo_root: Repository root directory
            branch: Name of the branch to get the stack for

        Returns:
            List of branch names in the stack, ordered from trunk to leaf
            (e.g., ["main", "feature-1", "feature-2", "feature-3"]).
            Returns None if branch is not tracked by graphite
        """
        ...

    @abstractmethod
    def track_branch(self, cwd: Path, branch_name: str, parent_branch: str) -> None:
        """Track a branch with Graphite.

        Uses `gt track` to register a branch in Graphite's cache. This is needed
        when branches are created with direct git operations (git branch) instead
        of gt create.

        Args:
            cwd: Working directory where gt track should run
            branch_name: Name of the branch to track
            parent_branch: Name of the parent branch in the stack
        """
        ...

    @abstractmethod
    def submit_branch(self, repo_root: Path, branch_name: str, *, quiet: bool) -> None:
        """Submit (force-push) a branch to GitHub.

        Uses `gt submit` to push a branch that was rebased by `gt sync -f`.
        This is typically called after merging a PR to push the rebased remaining
        branches in a stack to GitHub.

        Args:
            repo_root: Repository root directory
            branch_name: Name of the branch to submit
            quiet: If True, pass --quiet flag to gt submit for minimal output
        """
        ...

    def get_parent_branch(self, git_ops: Git, repo_root: Path, branch: str) -> str | None:
        """Get parent branch name for a given branch.

        This is a convenience helper that calls get_all_branches() and extracts
        the parent relationship. All implementations inherit this method.

        Args:
            git_ops: Git instance for accessing git common directory
            repo_root: Repository root directory
            branch: Name of the branch to get the parent for

        Returns:
            Parent branch name, or None if:
            - Branch is not tracked by graphite
            - Branch has no parent (is trunk)
        """
        all_branches = self.get_all_branches(git_ops, repo_root)
        if branch not in all_branches:
            return None
        return all_branches[branch].parent

    def get_child_branches(self, git_ops: Git, repo_root: Path, branch: str) -> list[str]:
        """Get child branch names for a given branch.

        This is a convenience helper that calls get_all_branches() and extracts
        the children relationship. All implementations inherit this method.

        Args:
            git_ops: Git instance for accessing git common directory
            repo_root: Repository root directory
            branch: Name of the branch to get children for

        Returns:
            List of child branch names, or empty list if:
            - Branch is not tracked by graphite
            - Branch has no children
        """
        all_branches = self.get_all_branches(git_ops, repo_root)
        if branch not in all_branches:
            return []
        return all_branches[branch].children
