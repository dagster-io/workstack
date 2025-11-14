"""High-level GitHub operations interface.

This module provides a clean abstraction over GitHub CLI (gh) calls, making the
codebase more testable and maintainable.

Architecture:
- GitHubOps: Abstract base class defining the interface
- RealGitHubOps: Production implementation using gh CLI
- DryRunGitHubOps: Dry-run wrapper that delegates reads, prints write intentions
- Standalone functions: Convenience wrappers if needed
"""

import json
import re
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NamedTuple

from workstack.cli.output import user_output
from workstack.core.printing_ops_base import PrintingOpsBase

PRState = Literal["OPEN", "MERGED", "CLOSED", "NONE"]


class PRInfo(NamedTuple):
    """PR status information from GitHub API."""

    state: PRState
    pr_number: int | None
    title: str | None


def execute_gh_command(cmd: list[str], cwd: Path) -> str:
    """Execute a gh CLI command and return stdout.

    Args:
        cmd: Command and arguments to execute
        cwd: Working directory for command execution

    Returns:
        stdout from the command

    Raises:
        subprocess.CalledProcessError: If command fails
        FileNotFoundError: If gh is not installed
    """
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout


def parse_github_pr_list(json_str: str, include_checks: bool) -> dict[str, "PullRequestInfo"]:
    """Parse gh pr list JSON output into PullRequestInfo objects.

    Args:
        json_str: JSON string from gh pr list command
        include_checks: Whether check status is included in JSON

    Returns:
        Mapping of branch name to PullRequestInfo
    """
    prs_data = json.loads(json_str)
    prs = {}

    for pr in prs_data:
        branch = pr["headRefName"]

        # Only determine check status if we fetched it
        checks_passing = None
        if include_checks and "statusCheckRollup" in pr:
            checks_passing = _determine_checks_status(pr["statusCheckRollup"])

        # Parse owner and repo from GitHub URL
        url = pr["url"]
        parsed = _parse_github_pr_url(url)
        if parsed is None:
            # Skip PRs with malformed URLs (shouldn't happen in practice)
            continue
        owner, repo = parsed

        prs[branch] = PullRequestInfo(
            number=pr["number"],
            state=pr["state"],
            url=url,
            is_draft=pr["isDraft"],
            checks_passing=checks_passing,
            owner=owner,
            repo=repo,
        )

    return prs


def parse_github_pr_status(json_str: str) -> PRInfo:
    """Parse gh pr status JSON output.

    Args:
        json_str: JSON string from gh pr list command for a specific branch

    Returns:
        PRInfo with state, pr_number, and title
        - state: "OPEN", "MERGED", "CLOSED", or "NONE" if no PR exists
        - pr_number: PR number or None if no PR exists
        - title: PR title or None if no PR exists
    """
    prs_data = json.loads(json_str)

    # If no PR exists for this branch
    if not prs_data:
        return PRInfo("NONE", None, None)

    # Take the first (and should be only) PR
    pr = prs_data[0]
    return PRInfo(pr["state"], pr["number"], pr["title"])


def _determine_checks_status(check_rollup: list[dict]) -> bool | None:
    """Determine overall CI checks status.

    Returns:
        None if no checks configured
        True if all checks passed (SUCCESS, SKIPPED, or NEUTRAL)
        False if any check failed or is pending
    """
    if not check_rollup:
        return None

    # GitHub check conclusions that should be treated as passing
    passing_conclusions = {"SUCCESS", "SKIPPED", "NEUTRAL"}

    for check in check_rollup:
        status = check.get("status")
        conclusion = check.get("conclusion")

        # If any check is not completed, consider it failing
        if status != "COMPLETED":
            return False

        # If any completed check didn't pass, consider it failing
        if conclusion not in passing_conclusions:
            return False

    return True


def _parse_github_pr_url(url: str) -> tuple[str, str] | None:
    """Parse owner and repo from GitHub PR URL.

    Args:
        url: GitHub PR URL (e.g., "https://github.com/owner/repo/pull/123")

    Returns:
        Tuple of (owner, repo) or None if URL doesn't match expected pattern

    Example:
        >>> _parse_github_pr_url("https://github.com/dagster-io/workstack/pull/23")
        ("dagster-io", "workstack")
    """
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)/pull/\d+", url)
    if match:
        return (match.group(1), match.group(2))
    return None


@dataclass(frozen=True)
class PullRequestInfo:
    """Information about a GitHub pull request."""

    number: int
    state: str  # "OPEN", "MERGED", "CLOSED"
    url: str
    is_draft: bool
    checks_passing: bool | None  # None if no checks, True if all pass, False if any fail
    owner: str  # GitHub repo owner (e.g., "schrockn")
    repo: str  # GitHub repo name (e.g., "workstack")


@dataclass(frozen=True)
class PRMergeability:
    """GitHub PR mergeability status."""

    mergeable: str  # "MERGEABLE", "CONFLICTING", "UNKNOWN"
    merge_state_status: str  # "CLEAN", "BLOCKED", "UNSTABLE", "DIRTY", etc.


class GitHubOps(ABC):
    """Abstract interface for GitHub operations.

    All implementations (real and fake) must implement this interface.
    """

    @abstractmethod
    def get_prs_for_repo(
        self, repo_root: Path, *, include_checks: bool
    ) -> dict[str, PullRequestInfo]:
        """Get PR information for all branches in the repository.

        Args:
            repo_root: Repository root directory
            include_checks: If True, fetch CI check status (slower). If False, skip check status

        Returns:
            Mapping of branch name -> PullRequestInfo
            - checks_passing is None when include_checks=False
            Empty dict if gh CLI is not available or not authenticated
        """
        ...

    @abstractmethod
    def get_pr_status(self, repo_root: Path, branch: str, *, debug: bool) -> PRInfo:
        """Get PR status for a specific branch.

        Args:
            repo_root: Repository root directory
            branch: Branch name to check
            debug: If True, print debug information

        Returns:
            PRInfo with state, pr_number, and title
            - state: "OPEN", "MERGED", "CLOSED", or "NONE" if no PR exists
            - pr_number: PR number or None if no PR exists
            - title: PR title or None if no PR exists
        """
        ...

    @abstractmethod
    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str | None:
        """Get current base branch of a PR from GitHub.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to query

        Returns:
            Name of the base branch, or None if query fails
        """
        ...

    @abstractmethod
    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """Update base branch of a PR on GitHub.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to update
            new_base: New base branch name
        """
        ...

    @abstractmethod
    def get_pr_mergeability(self, repo_root: Path, pr_number: int) -> PRMergeability | None:
        """Get PR mergeability status from GitHub.

        Returns None if PR not found or API error.
        """
        ...

    @abstractmethod
    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
    ) -> None:
        """Merge a pull request on GitHub.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to merge
            squash: If True, use squash merge strategy (default: True)
            verbose: If True, show detailed output
        """
        ...


class RealGitHubOps(GitHubOps):
    """Production implementation using gh CLI.

    All GitHub operations execute actual gh commands via subprocess.
    """

    def __init__(self, execute_fn=None):
        """Initialize RealGitHubOps with optional command executor.

        Args:
            execute_fn: Optional function to execute commands (for testing).
                       If None, uses execute_gh_command.
        """
        self._execute = execute_fn or execute_gh_command

    def get_prs_for_repo(
        self, repo_root: Path, *, include_checks: bool
    ) -> dict[str, PullRequestInfo]:
        """Get PR information for all branches in the repository.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        try:
            # Build JSON fields list - conditionally include statusCheckRollup for performance
            json_fields = "number,headRefName,url,state,isDraft"
            if include_checks:
                json_fields += ",statusCheckRollup"

            cmd = [
                "gh",
                "pr",
                "list",
                "--state",
                "all",
                "--json",
                json_fields,
            ]
            stdout = self._execute(cmd, repo_root)
            return parse_github_pr_list(stdout, include_checks)

        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            # gh not installed, not authenticated, or JSON parsing failed
            return {}

    def get_pr_status(self, repo_root: Path, branch: str, *, debug: bool) -> PRInfo:
        """Get PR status for a specific branch.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        try:
            # Query gh for PR info for this specific branch
            cmd = [
                "gh",
                "pr",
                "list",
                "--head",
                branch,
                "--state",
                "all",
                "--json",
                "number,state,title",
                "--limit",
                "1",
            ]

            if debug:
                user_output(f"$ {' '.join(cmd)}")

            stdout = self._execute(cmd, repo_root)
            return parse_github_pr_status(stdout)

        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            # gh not installed, not authenticated, or JSON parsing failed
            return PRInfo("NONE", None, None)

    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str | None:
        """Get current base branch of a PR from GitHub.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        try:
            cmd = [
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--json",
                "baseRefName",
                "--jq",
                ".baseRefName",
            ]
            stdout = self._execute(cmd, repo_root)
            return stdout.strip()

        except (subprocess.CalledProcessError, FileNotFoundError):
            # gh not installed, not authenticated, or command failed
            return None

    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """Update base branch of a PR on GitHub.

        Gracefully handles gh CLI availability issues (not installed, not authenticated).
        The calling code should validate preconditions (PR exists, is open, new base exists)
        before calling this method.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability. Genuine command failures (invalid PR, invalid base) should be
        caught by precondition checks in the caller.
        """
        try:
            cmd = ["gh", "pr", "edit", str(pr_number), "--base", new_base]
            self._execute(cmd, repo_root)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # gh not installed, not authenticated, or command failed
            # Graceful degradation - operation skipped
            # Caller is responsible for precondition validation
            pass

    def get_pr_mergeability(self, repo_root: Path, pr_number: int) -> PRMergeability | None:
        """Get PR mergeability status from GitHub via gh CLI.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        try:
            result = subprocess.run(
                ["gh", "pr", "view", str(pr_number), "--json", "mergeable,mergeStateStatus"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
            )
            data = json.loads(result.stdout)
            return PRMergeability(
                mergeable=data["mergeable"],
                merge_state_status=data["mergeStateStatus"],
            )
        except (
            subprocess.CalledProcessError,
            json.JSONDecodeError,
            KeyError,
            FileNotFoundError,
        ):
            return None

    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
    ) -> None:
        """Merge a pull request on GitHub via gh CLI."""
        cmd = ["gh", "pr", "merge", str(pr_number)]
        if squash:
            cmd.append("--squash")

        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )

        # Show output in verbose mode
        if verbose and result.stdout:
            user_output(result.stdout)


# ============================================================================
# No-op Wrapper
# ============================================================================


class NoopGitHubOps(GitHubOps):
    """No-op wrapper for GitHub operations.

    Read operations are delegated to the wrapped implementation.
    Write operations return without executing (no-op behavior).

    This wrapper prevents destructive GitHub operations from executing in dry-run mode,
    while still allowing read operations for validation.
    """

    def __init__(self, wrapped: GitHubOps) -> None:
        """Initialize dry-run wrapper with a real implementation.

        Args:
            wrapped: The real GitHub operations implementation to wrap
        """
        self._wrapped = wrapped

    def get_prs_for_repo(
        self, repo_root: Path, *, include_checks: bool
    ) -> dict[str, PullRequestInfo]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_prs_for_repo(repo_root, include_checks=include_checks)

    def get_pr_status(self, repo_root: Path, branch: str, *, debug: bool) -> PRInfo:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_pr_status(repo_root, branch, debug=debug)

    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str | None:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_pr_base_branch(repo_root, pr_number)

    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """No-op for updating PR base branch in dry-run mode."""
        # Do nothing - prevents actual PR base update
        pass

    def get_pr_mergeability(self, repo_root: Path, pr_number: int) -> PRMergeability | None:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_pr_mergeability(repo_root, pr_number)

    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
    ) -> None:
        """No-op for merging PR in dry-run mode."""
        # Do nothing - prevents actual PR merge
        pass


# ============================================================================
# Printing Wrapper Implementation
# ============================================================================


class PrintingGitHubOps(PrintingOpsBase, GitHubOps):
    """Wrapper that prints operations before delegating to inner implementation.

    This wrapper prints styled output for operations, then delegates to the
    wrapped implementation (which could be Real or Noop).

    Usage:
        # For production
        printing_ops = PrintingGitHubOps(real_ops, script_mode=False, dry_run=False)

        # For dry-run
        noop_inner = NoopGitHubOps(real_ops)
        printing_ops = PrintingGitHubOps(noop_inner, script_mode=False, dry_run=True)
    """

    # Inherits __init__, _emit, and _format_command from PrintingOpsBase

    # Read-only operations: delegate without printing

    def get_prs_for_repo(
        self, repo_root: Path, *, include_checks: bool
    ) -> dict[str, PullRequestInfo]:
        """Get PRs (read-only, no printing)."""
        return self._wrapped.get_prs_for_repo(repo_root, include_checks=include_checks)

    def get_pr_status(self, repo_root: Path, branch: str, *, debug: bool) -> PRInfo:
        """Get PR status (read-only, no printing)."""
        return self._wrapped.get_pr_status(repo_root, branch, debug=debug)

    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str | None:
        """Get PR base branch (read-only, no printing)."""
        return self._wrapped.get_pr_base_branch(repo_root, pr_number)

    def get_pr_mergeability(self, repo_root: Path, pr_number: int) -> PRMergeability | None:
        """Get PR mergeability (read-only, no printing)."""
        return self._wrapped.get_pr_mergeability(repo_root, pr_number)

    # Operations that need printing

    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """Update PR base branch with printed output."""
        self._emit(self._format_command(f"gh pr edit {pr_number} --base {new_base}"))
        self._wrapped.update_pr_base_branch(repo_root, pr_number, new_base)

    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
    ) -> None:
        """Merge PR with printed output."""
        merge_type = "--squash" if squash else "--merge"
        self._emit(self._format_command(f"gh pr merge {pr_number} {merge_type}"))
        self._wrapped.merge_pr(repo_root, pr_number, squash=squash, verbose=verbose)
