"""GitHub issues integration for erk plan storage."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from erk.core.github.parsing import execute_gh_command


@dataclass(frozen=True)
class IssueInfo:
    """Information about a GitHub issue."""

    number: int
    title: str
    body: str
    state: str  # "OPEN" or "CLOSED"
    url: str


class GitHubIssues(ABC):
    """Abstract interface for GitHub issue operations.

    All implementations (real and fake) must implement this interface.
    """

    @abstractmethod
    def create_issue(self, repo_root: Path, title: str, body: str, labels: list[str]) -> int:
        """Create a new GitHub issue.

        Args:
            repo_root: Repository root directory
            title: Issue title
            body: Issue body markdown
            labels: List of label names to apply

        Returns:
            Issue number of the created issue

        Raises:
            RuntimeError: If gh CLI fails (not installed, not authenticated, or command error)
        """
        ...

    @abstractmethod
    def get_issue(self, repo_root: Path, number: int) -> IssueInfo:
        """Fetch issue data by number.

        Args:
            repo_root: Repository root directory
            number: Issue number to fetch

        Returns:
            IssueInfo with title, body, state, and url

        Raises:
            RuntimeError: If gh CLI fails or issue not found
        """
        ...

    @abstractmethod
    def add_comment(self, repo_root: Path, number: int, body: str) -> None:
        """Add a comment to an existing issue.

        Args:
            repo_root: Repository root directory
            number: Issue number to comment on
            body: Comment body markdown

        Raises:
            RuntimeError: If gh CLI fails or issue not found
        """
        ...

    @abstractmethod
    def list_issues(
        self,
        repo_root: Path,
        labels: list[str] | None = None,
        state: str | None = None,
    ) -> list[IssueInfo]:
        """Query issues by criteria.

        Args:
            repo_root: Repository root directory
            labels: Filter by labels (all labels must match)
            state: Filter by state ("open", "closed", or "all")

        Returns:
            List of IssueInfo matching the criteria

        Raises:
            RuntimeError: If gh CLI fails
        """
        ...

    @abstractmethod
    def ensure_label_exists(
        self,
        repo_root: Path,
        label: str,
        description: str,
        color: str,
    ) -> None:
        """Ensure a label exists in the repository, creating it if needed.

        Args:
            repo_root: Repository root directory
            label: Label name to ensure exists
            description: Label description (used if creating)
            color: Label color hex code without '#' (used if creating)

        Raises:
            RuntimeError: If gh CLI fails (not installed, not authenticated, or command error)
        """
        ...


class RealGitHubIssues(GitHubIssues):
    """Production implementation using gh CLI.

    All GitHub issue operations execute actual gh commands via subprocess.
    """

    def __init__(self, execute_fn=None):
        """Initialize RealGitHubIssues with optional command executor.

        Args:
            execute_fn: Optional function to execute commands (for testing).
                       If None, uses execute_gh_command.
        """
        self._execute = execute_fn or execute_gh_command

    def create_issue(self, repo_root: Path, title: str, body: str, labels: list[str]) -> int:
        """Create a new GitHub issue using gh CLI.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, etc.).
        """
        cmd = ["gh", "issue", "create", "--title", title, "--body", body]
        for label in labels:
            cmd.extend(["--label", label])
        cmd.extend(["--json", "number", "--jq", ".number"])

        stdout = self._execute(cmd, repo_root)
        return int(stdout.strip())

    def get_issue(self, repo_root: Path, number: int) -> IssueInfo:
        """Fetch issue data using gh CLI.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        """
        cmd = [
            "gh",
            "issue",
            "view",
            str(number),
            "--json",
            "number,title,body,state,url",
        ]
        stdout = self._execute(cmd, repo_root)
        data = json.loads(stdout)

        return IssueInfo(
            number=data["number"],
            title=data["title"],
            body=data["body"],
            state=data["state"],
            url=data["url"],
        )

    def add_comment(self, repo_root: Path, number: int, body: str) -> None:
        """Add comment to issue using gh CLI.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        """
        cmd = ["gh", "issue", "comment", str(number), "--body", body]
        self._execute(cmd, repo_root)

    def list_issues(
        self,
        repo_root: Path,
        labels: list[str] | None = None,
        state: str | None = None,
    ) -> list[IssueInfo]:
        """Query issues using gh CLI.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated).
        """
        cmd = ["gh", "issue", "list", "--json", "number,title,body,state,url"]

        if labels:
            for label in labels:
                cmd.extend(["--label", label])

        if state:
            cmd.extend(["--state", state])

        stdout = self._execute(cmd, repo_root)
        data = json.loads(stdout)

        return [
            IssueInfo(
                number=issue["number"],
                title=issue["title"],
                body=issue["body"],
                state=issue["state"],
                url=issue["url"],
            )
            for issue in data
        ]

    def ensure_label_exists(
        self,
        repo_root: Path,
        label: str,
        description: str,
        color: str,
    ) -> None:
        """Ensure label exists in repository, creating it if needed.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated).
        """
        # Check if label exists
        check_cmd = [
            "gh",
            "label",
            "list",
            "--json",
            "name",
            "--jq",
            f'.[] | select(.name == "{label}") | .name',
        ]
        stdout = self._execute(check_cmd, repo_root)

        # If label doesn't exist (empty output), create it
        if not stdout.strip():
            create_cmd = [
                "gh",
                "label",
                "create",
                label,
                "--description",
                description,
                "--color",
                color,
            ]
            self._execute(create_cmd, repo_root)


class FakeGitHubIssues(GitHubIssues):
    """In-memory fake implementation for testing.

    All state is provided via constructor using keyword arguments.
    """

    def __init__(
        self,
        *,
        issues: dict[int, IssueInfo] | None = None,
        next_issue_number: int = 1,
        labels: set[str] | None = None,
    ) -> None:
        """Create FakeGitHubIssues with pre-configured state.

        Args:
            issues: Mapping of issue number -> IssueInfo
            next_issue_number: Next issue number to assign (for predictable testing)
            labels: Set of existing label names in the repository
        """
        self._issues = issues or {}
        self._next_issue_number = next_issue_number
        self._labels = labels or set()
        self._created_issues: list[tuple[str, str, list[str]]] = []
        self._added_comments: list[tuple[int, str]] = []
        self._created_labels: list[tuple[str, str, str]] = []

    @property
    def created_issues(self) -> list[tuple[str, str, list[str]]]:
        """Read-only access to created issues for test assertions.

        Returns list of (title, body, labels) tuples.
        """
        return self._created_issues

    @property
    def added_comments(self) -> list[tuple[int, str]]:
        """Read-only access to added comments for test assertions.

        Returns list of (issue_number, body) tuples.
        """
        return self._added_comments

    @property
    def created_labels(self) -> list[tuple[str, str, str]]:
        """Read-only access to created labels for test assertions.

        Returns list of (label, description, color) tuples.
        """
        return self._created_labels

    @property
    def labels(self) -> set[str]:
        """Read-only access to label names in the repository.

        Returns set of label names.
        """
        return self._labels.copy()

    def create_issue(self, repo_root: Path, title: str, body: str, labels: list[str]) -> int:
        """Create issue in fake storage and track mutation."""
        issue_number = self._next_issue_number
        self._next_issue_number += 1

        self._issues[issue_number] = IssueInfo(
            number=issue_number,
            title=title,
            body=body,
            state="OPEN",
            url=f"https://github.com/owner/repo/issues/{issue_number}",
        )
        self._created_issues.append((title, body, labels))

        return issue_number

    def get_issue(self, repo_root: Path, number: int) -> IssueInfo:
        """Get issue from fake storage.

        Raises:
            RuntimeError: If issue number not found (simulates gh CLI error)
        """
        if number not in self._issues:
            msg = f"Issue #{number} not found"
            raise RuntimeError(msg)
        return self._issues[number]

    def add_comment(self, repo_root: Path, number: int, body: str) -> None:
        """Record comment in mutation tracking.

        Raises:
            RuntimeError: If issue number not found (simulates gh CLI error)
        """
        if number not in self._issues:
            msg = f"Issue #{number} not found"
            raise RuntimeError(msg)
        self._added_comments.append((number, body))

    def list_issues(
        self,
        repo_root: Path,
        labels: list[str] | None = None,
        state: str | None = None,
    ) -> list[IssueInfo]:
        """Query issues from fake storage.

        Note: label filtering is not implemented in fake - returns all issues
        matching state filter. This is acceptable for testing since we control
        the fake's state.
        """
        issues = list(self._issues.values())

        if state and state != "all":
            state_upper = state.upper()
            issues = [issue for issue in issues if issue.state == state_upper]

        return issues

    def ensure_label_exists(
        self,
        repo_root: Path,
        label: str,
        description: str,
        color: str,
    ) -> None:
        """Ensure label exists in fake storage, creating if needed."""
        if label not in self._labels:
            self._labels.add(label)
            self._created_labels.append((label, description, color))


class NoopGitHubIssues(GitHubIssues):
    """No-op wrapper for GitHub issue operations.

    Read operations are delegated to the wrapped implementation.
    Write operations return without executing (no-op behavior).

    This wrapper prevents issue mutations from executing in dry-run mode,
    while still allowing read operations for validation.
    """

    def __init__(self, wrapped: GitHubIssues) -> None:
        """Initialize dry-run wrapper with a real implementation.

        Args:
            wrapped: The real GitHubIssues implementation to wrap
        """
        self._wrapped = wrapped

    def create_issue(self, repo_root: Path, title: str, body: str, labels: list[str]) -> int:
        """No-op for creating issue in dry-run mode.

        Returns a fake issue number (1) to allow dry-run workflows to continue.
        """
        return 1

    def get_issue(self, repo_root: Path, number: int) -> IssueInfo:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_issue(repo_root, number)

    def add_comment(self, repo_root: Path, number: int, body: str) -> None:
        """No-op for adding comment in dry-run mode."""
        pass

    def list_issues(
        self,
        repo_root: Path,
        labels: list[str] | None = None,
        state: str | None = None,
    ) -> list[IssueInfo]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.list_issues(repo_root, labels=labels, state=state)

    def ensure_label_exists(
        self,
        repo_root: Path,
        label: str,
        description: str,
        color: str,
    ) -> None:
        """No-op for ensuring label exists in dry-run mode."""
        pass
