"""Abstract operations interfaces for GT kit subprocess commands.

This module defines ABC interfaces for git, Graphite (gt), and GitHub (gh) operations
used by GT kit CLI commands. These interfaces enable dependency injection with
in-memory fakes for testing while maintaining type safety.

Design:
- Three separate ABC interfaces: GitGtKitOps, GraphiteGtKitOps, GitHubGtKitOps
- Composite GtKitOps interface that combines all three
- Return values match existing subprocess patterns (str | None, bool, etc.)
- LBYL pattern: operations check state, return None/False on failure
"""

from abc import ABC, abstractmethod

from erk_shared.integrations.gt.types import CommandResult


class GitGtKit(ABC):
    """Git operations interface for GT kit commands."""

    @abstractmethod
    def get_current_branch(self) -> str | None:
        """Get the name of the current branch.

        Returns:
            Branch name or None if command fails
        """

    @abstractmethod
    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes.

        Returns:
            True if changes exist, False otherwise
        """

    @abstractmethod
    def add_all(self) -> bool:
        """Stage all changes for commit.

        Returns:
            True on success, False on failure
        """

    @abstractmethod
    def commit(self, message: str) -> bool:
        """Create a commit with the given message.

        Args:
            message: Commit message

        Returns:
            True on success, False on failure
        """

    @abstractmethod
    def amend_commit(self, message: str) -> bool:
        """Amend the current commit with a new message.

        Args:
            message: New commit message

        Returns:
            True on success, False on failure
        """

    @abstractmethod
    def count_commits_in_branch(self, parent_branch: str) -> int:
        """Count commits in current branch compared to parent.

        Args:
            parent_branch: Name of the parent branch

        Returns:
            Number of commits, 0 if command fails
        """

    @abstractmethod
    def get_trunk_branch(self) -> str:
        """Get the trunk branch name for the repository.

        Detects the trunk branch by checking git's remote HEAD reference,
        falling back to common trunk branch names if detection fails.

        Returns:
            Trunk branch name (e.g., 'main', 'master')
        """

    @abstractmethod
    def get_repository_root(self) -> str:
        """Get the absolute path to the repository root.

        Returns:
            Absolute path to repo root

        Raises:
            subprocess.CalledProcessError: If not in a git repository
        """

    @abstractmethod
    def get_diff_to_parent(self, parent_branch: str) -> str:
        """Get git diff between parent branch and HEAD.

        Args:
            parent_branch: Name of the parent branch

        Returns:
            Full diff output as string

        Raises:
            subprocess.CalledProcessError: If diff command fails
        """

    @abstractmethod
    def check_merge_conflicts(self, base_branch: str, head_branch: str) -> bool:
        """Check if merging head_branch into base_branch would have conflicts.

        Uses git merge-tree to simulate merge without touching working tree.

        Args:
            base_branch: Base branch name (e.g., "master", "main")
            head_branch: Head branch name (current branch)

        Returns:
            True if conflicts detected, False otherwise
        """


class GraphiteGtKit(ABC):
    """Graphite (gt) operations interface for GT kit commands."""

    @abstractmethod
    def get_parent_branch(self) -> str | None:
        """Get the parent branch using gt parent.

        Returns:
            Parent branch name or None if command fails
        """

    @abstractmethod
    def get_children_branches(self) -> list[str]:
        """Get list of child branches using gt children.

        Returns:
            List of child branch names, empty list if command fails
        """

    @abstractmethod
    def squash_commits(self) -> CommandResult:
        """Run gt squash to consolidate commits.

        Returns:
            CommandResult with success status and output
        """

    @abstractmethod
    def submit(self, publish: bool = False, restack: bool = False) -> CommandResult:
        """Run gt submit to create or update PR.

        Args:
            publish: Whether to use --publish flag
            restack: Whether to use --restack flag

        Returns:
            CommandResult with success status and output
        """

    @abstractmethod
    def restack(self) -> CommandResult:
        """Run gt restack in no-interactive mode.

        Returns:
            CommandResult with success status and output
        """

    @abstractmethod
    def navigate_to_child(self) -> bool:
        """Navigate to child branch using gt up.

        Returns:
            True on success, False on failure
        """

    @abstractmethod
    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Check Graphite authentication status.

        Returns:
            Tuple of (is_authenticated, username, repo_info):
            - is_authenticated: True if gt is authenticated
            - username: Authenticated username or None
            - repo_info: Repository info string or None
        """


class GitHubGtKit(ABC):
    """GitHub (gh) operations interface for GT kit commands."""

    @abstractmethod
    def get_pr_info(self) -> tuple[int, str] | None:
        """Get PR number and URL for current branch.

        Returns:
            Tuple of (number, url) or None if no PR exists
        """

    @abstractmethod
    def get_pr_state(self) -> tuple[int, str] | None:
        """Get PR number and state for current branch.

        Returns:
            Tuple of (number, state) or None if no PR exists
        """

    @abstractmethod
    def update_pr_metadata(self, title: str, body: str) -> bool:
        """Update PR title and body using gh pr edit.

        Args:
            title: New PR title
            body: New PR body

        Returns:
            True on success, False on failure
        """

    @abstractmethod
    def mark_pr_ready(self) -> bool:
        """Mark PR as ready for review using gh pr ready.

        Converts a draft PR to ready status. If PR is already ready, this is a no-op.

        Returns:
            True on success, False on failure
        """

    @abstractmethod
    def merge_pr(self) -> bool:
        """Merge the PR using squash merge.

        Returns:
            True on success, False on failure
        """

    @abstractmethod
    def get_graphite_pr_url(self, pr_number: int) -> str | None:
        """Get Graphite PR URL for given PR number.

        Args:
            pr_number: PR number

        Returns:
            Graphite URL or None if repo info cannot be determined
        """

    @abstractmethod
    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Check GitHub CLI authentication status.

        Returns:
            Tuple of (is_authenticated, username, hostname):
            - is_authenticated: True if gh CLI is authenticated
            - username: Authenticated username or None
            - hostname: GitHub hostname or None
        """

    @abstractmethod
    def get_pr_diff(self, pr_number: int) -> str:
        """Get the diff for a PR using gh pr diff.

        Args:
            pr_number: PR number to get diff for

        Returns:
            Diff content as string

        Raises:
            subprocess.CalledProcessError: If gh command fails
        """

    @abstractmethod
    def get_pr_status(self, branch: str) -> tuple[int | None, str | None]:
        """Get PR number and URL for a specific branch.

        Args:
            branch: Branch name to check

        Returns:
            Tuple of (pr_number, pr_url) or (None, None) if no PR exists
        """

    @abstractmethod
    def get_pr_mergeability(self, pr_number: int) -> tuple[str, str]:
        """Get PR mergeability status from GitHub API.

        Args:
            pr_number: PR number to check

        Returns:
            Tuple of (mergeable, merge_state_status):
            - mergeable: "MERGEABLE", "CONFLICTING", or "UNKNOWN"
            - merge_state_status: "CLEAN", "DIRTY", "UNSTABLE", etc.
        """


class GtKit(ABC):
    """Composite interface combining all GT kit operations.

    This interface provides a single injection point for all git, Graphite,
    and GitHub operations used by GT kit CLI commands.
    """

    @abstractmethod
    def git(self) -> GitGtKit:
        """Get the git operations interface.

        Returns:
            GitGtKitOps implementation
        """

    @abstractmethod
    def graphite(self) -> GraphiteGtKit:
        """Get the Graphite operations interface.

        Returns:
            GraphiteGtKitOps implementation
        """

    @abstractmethod
    def github(self) -> GitHubGtKit:
        """Get the GitHub operations interface.

        Returns:
            GitHubGtKitOps implementation
        """
