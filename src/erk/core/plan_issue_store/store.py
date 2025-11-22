"""Abstract interface for plan issue storage providers."""

from abc import ABC, abstractmethod
from pathlib import Path

from erk.core.plan_issue_store.types import PlanIssue, PlanIssueQuery


class PlanIssueStore(ABC):
    """Abstract interface for plan issue operations.

    All implementations (real and fake) must implement this interface.
    This interface provides READ-only operations for plan issues.
    Write operations (create, comment, label) will be added in future versions.
    """

    @abstractmethod
    def get_plan_issue(self, repo_root: Path, plan_issue_identifier: str) -> PlanIssue:
        """Fetch a plan issue by identifier.

        Args:
            repo_root: Repository root directory
            plan_issue_identifier: Provider-specific identifier (e.g., "42", "PROJ-123")

        Returns:
            PlanIssue with all metadata

        Raises:
            RuntimeError: If provider fails or issue not found
        """
        ...

    @abstractmethod
    def list_plan_issues(self, repo_root: Path, query: PlanIssueQuery) -> list[PlanIssue]:
        """Query plan issues by criteria.

        Args:
            repo_root: Repository root directory
            query: Filter criteria (labels, state, assignee, limit)

        Returns:
            List of PlanIssue matching the criteria

        Raises:
            RuntimeError: If provider fails
        """
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of the provider.

        Returns:
            Provider name (e.g., "github", "gitlab", "linear")
        """
        ...
