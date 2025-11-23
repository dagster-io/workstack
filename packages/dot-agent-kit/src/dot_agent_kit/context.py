"""Application context with dependency injection.

This module provides the canonical context creation pattern for dot-agent-kit,
following the architecture established in erk's core/context.py.

The DotAgentContext dataclass holds all dependencies (GitHub integrations, config)
and is created once at CLI entry point, then threaded through the application.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

import click
from erk_shared.github.issues import GitHubIssues, RealGitHubIssues


@dataclass(frozen=True)
class DotAgentContext:
    """Immutable context holding all dependencies for dot-agent-kit operations.

    Created at CLI entry point via create_context() and threaded through
    the application via Click's context system. Frozen to prevent accidental
    modification at runtime.

    Attributes:
        github_issues: GitHub Issues integration for querying/commenting
        debug: Debug flag for error handling (full stack traces)
        repo_root: Repository root directory (detected at CLI entry)
    """

    github_issues: GitHubIssues
    debug: bool
    repo_root: Path

    @staticmethod
    def for_test(
        github_issues: GitHubIssues | None = None,
        debug: bool = False,
        repo_root: Path | None = None,
    ) -> "DotAgentContext":
        """Create test context with optional pre-configured implementations.

        Provides full control over all context parameters with sensible test defaults
        for any unspecified values. Uses fakes by default to avoid subprocess calls.

        Args:
            github_issues: Optional GitHubIssues implementation. If None, creates FakeGitHubIssues.
            debug: Whether to enable debug mode (default False).
            repo_root: Repository root path (defaults to Path("/fake/repo"))

        Returns:
            DotAgentContext configured with provided values and test defaults

        Example:
            >>> from erk_shared.github.issues import FakeGitHubIssues
            >>> github = FakeGitHubIssues()
            >>> ctx = DotAgentContext.for_test(
            ...     github_issues=github, debug=True, repo_root=Path("/tmp/test")
            ... )
        """
        from erk_shared.github.issues import FakeGitHubIssues

        # Provide defaults - ensures non-None values for type checker
        resolved_github_issues: GitHubIssues = (
            github_issues if github_issues is not None else FakeGitHubIssues()
        )
        resolved_repo_root: Path = repo_root if repo_root is not None else Path("/fake/repo")

        return DotAgentContext(
            github_issues=resolved_github_issues,
            debug=debug,
            repo_root=resolved_repo_root,
        )


def create_context(*, debug: bool) -> DotAgentContext:
    """Create production context with real implementations.

    This is the canonical factory for creating the application context.
    Called once at CLI entry point to create the context for the entire
    command execution.

    Detects repository root using git rev-parse. Exits with error if not in a git repository.

    Args:
        debug: If True, enable debug mode (full stack traces in error handling)

    Returns:
        DotAgentContext with real GitHub integrations and detected repo_root

    Example:
        >>> ctx = create_context(debug=False)
        >>> issue_number = ctx.github_issues.create_issue(ctx.repo_root, title, body, labels)
    """
    # Detect repo root using git rev-parse
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        click.echo("Error: Not in a git repository", err=True)
        raise SystemExit(1)

    return DotAgentContext(
        github_issues=RealGitHubIssues(),
        debug=debug,
        repo_root=Path(result.stdout.strip()),
    )
