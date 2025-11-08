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


class GitGtKitOps(ABC):
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


class GraphiteGtKitOps(ABC):
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
    def squash_commits(self) -> bool:
        """Run gt squash to consolidate commits.

        Returns:
            True on success, False on failure
        """

    @abstractmethod
    def submit(self, publish: bool = False, restack: bool = False) -> tuple[bool, str, str]:
        """Run gt submit to create or update PR.

        Args:
            publish: Whether to use --publish flag
            restack: Whether to use --restack flag

        Returns:
            Tuple of (success, stdout, stderr)
        """

    @abstractmethod
    def restack(self) -> bool:
        """Run gt restack in no-interactive mode.

        Returns:
            True on success, False on failure
        """

    @abstractmethod
    def navigate_to_child(self) -> bool:
        """Navigate to child branch using gt up.

        Returns:
            True on success, False on failure
        """


class GitHubGtKitOps(ABC):
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
    def merge_pr(self) -> bool:
        """Merge the PR using squash merge.

        Returns:
            True on success, False on failure
        """


class GtKitOps(ABC):
    """Composite interface combining all GT kit operations.

    This interface provides a single injection point for all git, Graphite,
    and GitHub operations used by GT kit CLI commands.
    """

    @abstractmethod
    def git(self) -> GitGtKitOps:
        """Get the git operations interface.

        Returns:
            GitGtKitOps implementation
        """

    @abstractmethod
    def graphite(self) -> GraphiteGtKitOps:
        """Get the Graphite operations interface.

        Returns:
            GraphiteGtKitOps implementation
        """

    @abstractmethod
    def github(self) -> GitHubGtKitOps:
        """Get the GitHub operations interface.

        Returns:
            GitHubGtKitOps implementation
        """
