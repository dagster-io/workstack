"""Fake GitHub CLI implementation for testing.

This module provides an in-memory fake implementation of DotAgentGitHubCli for testing.
It follows the immutable state pattern from erk's GT kit fakes.
"""

from dataclasses import dataclass, field

from dot_agent_kit.integrations.github_cli import DotAgentGitHubCli, IssueCreationResult


def _empty_str_list() -> list[str]:
    """Factory for empty string list (helps type inference)."""
    return []


@dataclass(frozen=True)
class GitHubIssueState:
    """Immutable state for a single GitHub issue."""

    number: int
    title: str
    body: str
    labels: list[str] = field(default_factory=_empty_str_list)
    state: str = "OPEN"
    comments: list[str] = field(default_factory=_empty_str_list)


def _empty_issue_dict() -> dict[int, GitHubIssueState]:
    """Factory for empty issue dict (helps type inference)."""
    return {}


@dataclass(frozen=True)
class GitHubState:
    """Immutable GitHub repository state."""

    issues: dict[int, GitHubIssueState] = field(default_factory=_empty_issue_dict)
    next_issue_number: int = 1


class FakeDotAgentGitHubCli(DotAgentGitHubCli):
    """In-memory fake implementation with immutable state.

    This fake uses mutable internal state (for test convenience) but exposes
    immutable query methods for assertions.

    Pattern matches erk's FakeGitHubIssues: constructor injection with keyword args,
    mutation tracking via properties, declarative setup methods.
    """

    def __init__(
        self,
        *,
        issues: dict[int, GitHubIssueState] | None = None,
        next_issue_number: int = 1,
    ) -> None:
        """Create FakeGitHubCli with pre-configured state.

        Args:
            issues: Mapping of issue number -> GitHubIssueState
            next_issue_number: Next issue number to assign (for predictable testing)
        """
        self._issues = issues or {}
        self._next_issue_number = next_issue_number
        self._created_issues: list[tuple[str, str, list[str]]] = []

    @property
    def created_issues(self) -> list[tuple[str, str, list[str]]]:
        """Read-only access to created issues for test assertions.

        Returns:
            List of (title, body, labels) tuples in creation order
        """
        return self._created_issues

    @property
    def issues(self) -> dict[int, GitHubIssueState]:
        """Read-only access to all issues.

        Returns:
            Mapping of issue number to GitHubIssueState
        """
        return self._issues.copy()

    def with_issue(
        self,
        number: int,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> "FakeDotAgentGitHubCli":
        """Declarative setup - add existing issue.

        Returns new FakeDotAgentGitHubCli instance with the issue added.

        Args:
            number: Issue number
            title: Issue title
            body: Issue body
            labels: List of label names (default: empty list)

        Returns:
            New FakeDotAgentGitHubCli instance with issue added
        """
        issue = GitHubIssueState(
            number=number,
            title=title,
            body=body,
            labels=labels or [],
        )
        new_issues = {**self._issues, number: issue}
        fake = FakeDotAgentGitHubCli(
            issues=new_issues,
            next_issue_number=self._next_issue_number,
        )
        # Preserve mutation tracking
        fake._created_issues = self._created_issues.copy()
        return fake

    def get_issue(self, number: int) -> GitHubIssueState | None:
        """Get issue by number for test assertions.

        Args:
            number: Issue number to retrieve

        Returns:
            GitHubIssueState if found, None otherwise
        """
        return self._issues.get(number)

    def create_issue(
        self,
        title: str,
        body: str,
        labels: list[str],
    ) -> IssueCreationResult:
        """Create issue in fake storage and track mutation.

        This mutates internal state but provides immutable query interface.
        """
        issue_number = self._next_issue_number
        self._next_issue_number += 1

        issue = GitHubIssueState(
            number=issue_number,
            title=title,
            body=body,
            labels=labels,
        )
        self._issues[issue_number] = issue
        self._created_issues.append((title, body, labels))

        url = f"https://github.com/owner/repo/issues/{issue_number}"
        return IssueCreationResult(
            success=True,
            issue_number=issue_number,
            issue_url=url,
        )
