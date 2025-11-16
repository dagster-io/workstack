"""Base class for status information collectors."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from erk.core.context import WorkstackContext


class StatusCollector(ABC):
    """Base class for status information collectors.

    Each collector is responsible for gathering a specific type of status
    information (git, PR, dependencies, etc.) and returning it in a structured
    format.

    Collectors should handle their own errors gracefully and return None
    if information cannot be collected.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name identifier for this collector."""
        ...

    @abstractmethod
    def is_available(self, ctx: WorkstackContext, worktree_path: Path) -> bool:
        """Check if this collector can run in the given worktree.

        Args:
            ctx: Workstack context with operations
            worktree_path: Path to the worktree

        Returns:
            True if collector can gather information, False otherwise
        """
        ...

    @abstractmethod
    def collect(self, ctx: WorkstackContext, worktree_path: Path, repo_root: Path) -> Any:
        """Collect status information from worktree.

        Args:
            ctx: Workstack context with operations
            worktree_path: Path to the worktree
            repo_root: Path to repository root

        Returns:
            Collected status data or None if collection fails
        """
        ...
