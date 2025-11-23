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


@dataclass(frozen=True)
class LabelResult:
    """Result of ensuring a label exists."""

    exists: bool  # True if label existed before call
    created: bool  # True if label was created by this call


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

    @abstractmethod
    def ensure_label_exists(
        self,
        label: str,
        description: str,
        color: str,
    ) -> LabelResult:
        """Ensure GitHub label exists, creating if needed.

        Args:
            label: Label name
            description: Label description for creation
            color: Hex color code (e.g., "0E8A16")

        Returns:
            LabelResult indicating if label existed or was created

        Note:
            Uses LBYL pattern - checks if label exists before attempting creation.
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

    def ensure_label_exists(
        self,
        label: str,
        description: str,
        color: str,
    ) -> LabelResult:
        """Ensure label exists using gh CLI.

        First checks if label exists, then creates it if needed.
        """
        # Check if label exists using gh CLI
        jq_filter = f'.[] | select(.name == "{label}") | .name'
        check_cmd = ["gh", "label", "list", "--json", "name", "--jq", jq_filter]
        check_result = subprocess.run(
            check_cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        # LBYL pattern: Check returncode and output
        if check_result.returncode == 0 and check_result.stdout.strip() == label:
            # Label exists
            return LabelResult(exists=True, created=False)

        # Label doesn't exist - create it
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
        create_result = subprocess.run(
            create_cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        # LBYL pattern: Check returncode
        if create_result.returncode != 0:
            # Creation failed - might be because label already exists
            # This is acceptable (non-blocking)
            return LabelResult(exists=True, created=False)

        # Label created successfully
        return LabelResult(exists=False, created=True)
