"""GitHub CLI integration for dot-agent-kit commands.

This module provides a thin abstraction layer over GitHub CLI operations
used by kit CLI commands. It follows the ABC/Real/Fake pattern for testability.
"""

import re
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class IssueCreationResult:
    """Result of creating a GitHub issue."""

    success: bool
    issue_number: int
    issue_url: str


class DotAgentGitHubCli(ABC):
    """Abstract interface for GitHub CLI operations.

    This interface defines the GitHub CLI operations needed by dot-agent-kit
    commands. All implementations (real and fake) must implement this interface.
    """

    @abstractmethod
    def create_issue(
        self,
        title: str,
        body: str,
        labels: list[str],
    ) -> IssueCreationResult:
        """Create a GitHub issue.

        Args:
            title: Issue title
            body: Issue body (markdown)
            labels: List of label names to apply

        Returns:
            IssueCreationResult with success flag, issue number, and URL

        Note:
            Uses LBYL pattern - returns success=False on error rather than raising exceptions.
        """
        ...


class RealDotAgentGitHubCli(DotAgentGitHubCli):
    """Real implementation using gh CLI via subprocess.

    This is a thin wrapper around subprocess calls to gh CLI. It contains
    NO business logic - only subprocess execution and minimal parsing.
    """

    def create_issue(
        self,
        title: str,
        body: str,
        labels: list[str],
    ) -> IssueCreationResult:
        """Create issue using gh CLI.

        Executes: gh issue create --title <title> --body-file - --label <labels>
        """
        # Build gh command with labels - use --body-file - to read from stdin
        cmd = ["gh", "issue", "create", "--title", title, "--body-file", "-"]
        for lbl in labels:
            cmd.extend(["--label", lbl])

        # Execute gh with body via stdin
        result = subprocess.run(
            cmd,
            input=body,
            capture_output=True,
            text=True,
            check=False,
        )

        # LBYL pattern: Check returncode before using stdout
        if result.returncode != 0:
            return IssueCreationResult(
                success=False,
                issue_number=-1,
                issue_url="",
            )

        # Parse URL from output (gh returns: https://github.com/owner/repo/issues/123)
        issue_url = result.stdout.strip()

        # Extract issue number from URL
        match = re.search(r"/issues/(\d+)$", issue_url)
        if not match:
            return IssueCreationResult(
                success=False,
                issue_number=-1,
                issue_url="",
            )

        issue_number = int(match.group(1))

        return IssueCreationResult(
            success=True,
            issue_number=issue_number,
            issue_url=issue_url,
        )
