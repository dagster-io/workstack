"""GitHub issues integration for erk plan storage."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from erk_shared.subprocess_utils import execute_gh_command


@dataclass(frozen=True)
class IssueInfo:
    """Information about a GitHub issue."""

    number: int
    title: str
    body: str
    state: str  # "OPEN" or "CLOSED"
    url: str
    labels: list[str]
    assignees: list[str]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class CreateIssueResult:
    """Result from creating a GitHub issue.

    Attributes:
        number: Issue number (e.g., 123)
        url: Full GitHub URL (e.g., https://github.com/owner/repo/issues/123)
    """

    number: int
    url: str


class GitHubIssues(ABC):
    """Abstract interface for GitHub issue operations.

    All implementations (real and fake) must implement this interface.
    """

    @abstractmethod
    def create_issue(
        self, repo_root: Path, title: str, body: str, labels: list[str]
    ) -> CreateIssueResult:
        """Create a new GitHub issue.

        Args:
            repo_root: Repository root directory
            title: Issue title
            body: Issue body markdown
            labels: List of label names to apply

        Returns:
            CreateIssueResult with issue number and full GitHub URL

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
        limit: int | None = None,
    ) -> list[IssueInfo]:
        """Query issues by criteria.

        Args:
            repo_root: Repository root directory
            labels: Filter by labels (all labels must match)
            state: Filter by state ("open", "closed", or "all")
            limit: Maximum number of issues to return (None = no limit)

        Returns:
            List of IssueInfo matching the criteria

        Raises:
            RuntimeError: If gh CLI fails
        """
        ...

    @abstractmethod
    def get_issue_comments(self, repo_root: Path, number: int) -> list[str]:
        """Fetch all comment bodies for an issue.

        Args:
            repo_root: Path to repository root
            number: Issue number

        Returns:
            List of comment bodies (markdown strings)

        Raises:
            RuntimeError: If gh CLI fails or issue not found
        """
        ...

    @abstractmethod
    def get_multiple_issue_comments(
        self, repo_root: Path, issue_numbers: list[int]
    ) -> dict[int, list[str]]:
        """Fetch comments for multiple issues in a single batch operation.

        Uses GitHub GraphQL API to fetch all issue comments in one request,
        significantly reducing API calls and improving performance.

        Args:
            repo_root: Path to repository root
            issue_numbers: List of issue numbers to fetch comments for

        Returns:
            Mapping of issue number to list of comment bodies (markdown strings).
            Issues without comments will have an empty list.

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

    @abstractmethod
    def ensure_label_on_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        """Ensure a label is present on an existing issue (idempotent).

        Args:
            repo_root: Repository root directory
            issue_number: Issue number to ensure label on
            label: Label name to ensure is present

        Raises:
            RuntimeError: If gh CLI fails or issue not found
        """
        ...


class RealGitHubIssues(GitHubIssues):
    """Production implementation using gh CLI.

    All GitHub issue operations execute actual gh commands via subprocess.
    """

    def __init__(self):
        """Initialize RealGitHubIssues."""

    def create_issue(
        self, repo_root: Path, title: str, body: str, labels: list[str]
    ) -> CreateIssueResult:
        """Create a new GitHub issue using gh CLI.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, etc.).
        """
        cmd = ["gh", "issue", "create", "--title", title, "--body", body]
        for label in labels:
            cmd.extend(["--label", label])

        stdout = execute_gh_command(cmd, repo_root)
        # gh issue create returns a URL like: https://github.com/owner/repo/issues/123
        url = stdout.strip()
        issue_number_str = url.rstrip("/").split("/")[-1]

        return CreateIssueResult(
            number=int(issue_number_str),
            url=url,
        )

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
            "number,title,body,state,url,labels,assignees,createdAt,updatedAt",
        ]
        stdout = execute_gh_command(cmd, repo_root)
        data = json.loads(stdout)

        return IssueInfo(
            number=data["number"],
            title=data["title"],
            body=data["body"],
            state=data["state"],
            url=data["url"],
            labels=[label["name"] for label in data.get("labels", [])],
            assignees=[assignee["login"] for assignee in data.get("assignees", [])],
            created_at=datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updatedAt"].replace("Z", "+00:00")),
        )

    def add_comment(self, repo_root: Path, number: int, body: str) -> None:
        """Add comment to issue using gh CLI.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        """
        cmd = ["gh", "issue", "comment", str(number), "--body", body]
        execute_gh_command(cmd, repo_root)

    def list_issues(
        self,
        repo_root: Path,
        labels: list[str] | None = None,
        state: str | None = None,
        limit: int | None = None,
    ) -> list[IssueInfo]:
        """Query issues using gh CLI.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated).
        """
        cmd = [
            "gh",
            "issue",
            "list",
            "--json",
            "number,title,body,state,url,labels,assignees,createdAt,updatedAt",
        ]

        if labels:
            for label in labels:
                cmd.extend(["--label", label])

        if state:
            cmd.extend(["--state", state])

        if limit is not None:
            cmd.extend(["--limit", str(limit)])

        stdout = execute_gh_command(cmd, repo_root)
        data = json.loads(stdout)

        return [
            IssueInfo(
                number=issue["number"],
                title=issue["title"],
                body=issue["body"],
                state=issue["state"],
                url=issue["url"],
                labels=[label["name"] for label in issue.get("labels", [])],
                assignees=[assignee["login"] for assignee in issue.get("assignees", [])],
                created_at=datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(issue["updatedAt"].replace("Z", "+00:00")),
            )
            for issue in data
        ]

    def get_issue_comments(self, repo_root: Path, number: int) -> list[str]:
        """Fetch all comment bodies for an issue using gh CLI.

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        """
        cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/issues/{number}/comments",
            "--jq",
            ".[].body",
        ]
        stdout = execute_gh_command(cmd, repo_root)

        if not stdout.strip():
            return []

        return stdout.strip().split("\n")

    def get_multiple_issue_comments(
        self, repo_root: Path, issue_numbers: list[int]
    ) -> dict[int, list[str]]:
        """Fetch comments for multiple issues using GraphQL batch query.

        Uses GraphQL aliases to fetch all issue comments in a single API call,
        dramatically improving performance (10-50x faster than individual calls).
        """
        if not issue_numbers:
            return {}

        # Build GraphQL query with aliases for each issue
        aliases = []
        for i, num in enumerate(issue_numbers):
            aliases.append(
                f"issue{i}: issue(number: {num}) {{ "
                f"number comments(first: 100) {{ nodes {{ body }} }} }}"
            )

        query = 'query { repository(owner: "$owner", name: "$repo") { ' + " ".join(aliases) + " } }"

        cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
        stdout = execute_gh_command(cmd, repo_root)
        data = json.loads(stdout)

        # Parse results into dict[issue_number -> comments]
        result: dict[int, list[str]] = {}
        repository = data.get("data", {}).get("repository", {})

        for i, num in enumerate(issue_numbers):
            issue_data = repository.get(f"issue{i}")
            if issue_data and issue_data.get("comments"):
                comments = [
                    node["body"] for node in issue_data["comments"]["nodes"] if node.get("body")
                ]
                result[num] = comments
            else:
                result[num] = []

        return result

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
        stdout = execute_gh_command(check_cmd, repo_root)

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
            execute_gh_command(create_cmd, repo_root)

    def ensure_label_on_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        """Ensure label is present on issue using gh CLI (idempotent).

        Note: Uses gh's native error handling - gh CLI raises RuntimeError
        on failures (not installed, not authenticated, issue not found).
        The gh CLI --add-label operation is idempotent.
        """
        cmd = ["gh", "issue", "edit", str(issue_number), "--add-label", label]
        execute_gh_command(cmd, repo_root)


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
        comments: dict[int, list[str]] | None = None,
    ) -> None:
        """Create FakeGitHubIssues with pre-configured state.

        Args:
            issues: Mapping of issue number -> IssueInfo
            next_issue_number: Next issue number to assign (for predictable testing)
            labels: Set of existing label names in the repository
            comments: Mapping of issue number -> list of comment bodies
        """
        self._issues = issues or {}
        self._next_issue_number = next_issue_number
        self._labels = labels or set()
        self._comments = comments or {}
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

    def create_issue(
        self, repo_root: Path, title: str, body: str, labels: list[str]
    ) -> CreateIssueResult:
        """Create issue in fake storage and track mutation."""
        issue_number = self._next_issue_number
        self._next_issue_number += 1

        # Create realistic fake URL for testing
        url = f"https://github.com/test-owner/test-repo/issues/{issue_number}"

        now = datetime.now(UTC)
        self._issues[issue_number] = IssueInfo(
            number=issue_number,
            title=title,
            body=body,
            state="OPEN",
            url=url,
            labels=labels,
            assignees=[],
            created_at=now,
            updated_at=now,
        )
        self._created_issues.append((title, body, labels))

        return CreateIssueResult(number=issue_number, url=url)

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
        limit: int | None = None,
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

        if limit is not None:
            issues = issues[:limit]

        return issues

    def get_issue_comments(self, repo_root: Path, number: int) -> list[str]:
        """Get comments for issue from fake storage.

        Returns:
            List of comment bodies, or empty list if no comments exist
        """
        return self._comments.get(number, [])

    def get_multiple_issue_comments(
        self, repo_root: Path, issue_numbers: list[int]
    ) -> dict[int, list[str]]:
        """Get comments for multiple issues from fake storage.

        Returns:
            Mapping of issue number to list of comment bodies.
            Issues without comments will have an empty list.
        """
        result: dict[int, list[str]] = {}
        for num in issue_numbers:
            result[num] = self._comments.get(num, [])
        return result

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

    def ensure_label_on_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        """Ensure label is present on issue in fake storage (idempotent).

        Raises:
            RuntimeError: If issue number not found (simulates gh CLI error)
        """
        if issue_number not in self._issues:
            msg = f"Issue #{issue_number} not found"
            raise RuntimeError(msg)

        # Get current issue and create updated version with new label (if not present)
        current_issue = self._issues[issue_number]
        if label not in current_issue.labels:
            updated_labels = current_issue.labels + [label]
            self._issues[issue_number] = IssueInfo(
                number=current_issue.number,
                title=current_issue.title,
                body=current_issue.body,
                state=current_issue.state,
                url=current_issue.url,
                labels=updated_labels,
                assignees=current_issue.assignees,
                created_at=current_issue.created_at,
                updated_at=current_issue.updated_at,
            )


class DryRunGitHubIssues(GitHubIssues):
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

    def create_issue(
        self, repo_root: Path, title: str, body: str, labels: list[str]
    ) -> CreateIssueResult:
        """No-op for creating issue in dry-run mode.

        Returns a fake CreateIssueResult to allow dry-run workflows to continue.
        """
        return CreateIssueResult(number=1, url="https://github.com/dry-run/dry-run/issues/1")

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
        limit: int | None = None,
    ) -> list[IssueInfo]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.list_issues(repo_root, labels=labels, state=state, limit=limit)

    def get_issue_comments(self, repo_root: Path, number: int) -> list[str]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_issue_comments(repo_root, number)

    def get_multiple_issue_comments(
        self, repo_root: Path, issue_numbers: list[int]
    ) -> dict[int, list[str]]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_multiple_issue_comments(repo_root, issue_numbers)

    def ensure_label_exists(
        self,
        repo_root: Path,
        label: str,
        description: str,
        color: str,
    ) -> None:
        """No-op for ensuring label exists in dry-run mode."""
        pass

    def ensure_label_on_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        """No-op for ensuring label in dry-run mode (idempotent)."""
        pass
