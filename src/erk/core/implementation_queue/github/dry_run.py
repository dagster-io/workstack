"""Dry-run wrapper for GitHub Actions admin operations."""

from pathlib import Path
from typing import Any

from erk.core.implementation_queue.github.abc import GitHubAdmin


class DryRunGitHubAdmin(GitHubAdmin):
    """Dry-run wrapper for GitHub Actions admin operations.

    Read operations are delegated to the wrapped implementation.
    Write operations return without executing (dry-run behavior).

    This wrapper prevents destructive GitHub admin operations from executing
    in dry-run mode, while still allowing read operations for validation.
    """

    def __init__(self, wrapped: GitHubAdmin) -> None:
        """Initialize dry-run wrapper with a real implementation.

        Args:
            wrapped: The real GitHubAdmin implementation to wrap
        """
        self._wrapped = wrapped

    def get_workflow_permissions(self, repo_root: Path) -> dict[str, Any]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_workflow_permissions(repo_root)

    def set_workflow_pr_permissions(self, repo_root: Path, enabled: bool) -> None:
        """No-op for setting workflow permissions in dry-run mode."""
        # Do nothing - prevents actual permission changes
        pass
