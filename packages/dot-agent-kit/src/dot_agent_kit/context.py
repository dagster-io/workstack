"""Application context with dependency injection.

This module provides the canonical context creation pattern for dot-agent-kit,
following the architecture established in erk's core/context.py.

The DotAgentContext dataclass holds all dependencies (GitHub integrations, config)
and is created once at CLI entry point, then threaded through the application.
"""

from dataclasses import dataclass

from dot_agent_kit.integrations.github_cli import (
    DotAgentGitHubCli,
    RealDotAgentGitHubCli,
)
from erk.core.github.issues import GitHubIssues, RealGitHubIssues


@dataclass(frozen=True)
class DotAgentContext:
    """Immutable context holding all dependencies for dot-agent-kit operations.

    Created at CLI entry point via create_context() and threaded through
    the application via Click's context system. Frozen to prevent accidental
    modification at runtime.

    Attributes:
        github_cli: GitHub CLI integration for creating issues
        github_issues: GitHub Issues integration for querying/commenting
        debug: Debug flag for error handling (full stack traces)
    """

    github_cli: DotAgentGitHubCli
    github_issues: GitHubIssues
    debug: bool

    @staticmethod
    def for_test(
        github_cli: DotAgentGitHubCli | None = None,
        github_issues: GitHubIssues | None = None,
        debug: bool = False,
    ) -> "DotAgentContext":
        """Create test context with optional pre-configured implementations.

        Provides full control over all context parameters with sensible test defaults
        for any unspecified values. Uses fakes by default to avoid subprocess calls.

        Args:
            github_cli: Optional GitHub CLI implementation. If None, creates FakeDotAgentGitHubCli.
            github_issues: Optional GitHubIssues implementation. If None, creates FakeGitHubIssues.
            debug: Whether to enable debug mode (default False).

        Returns:
            DotAgentContext configured with provided values and test defaults

        Example:
            >>> from tests.fakes.fake_github_cli import FakeDotAgentGitHubCli
            >>> github_cli = FakeDotAgentGitHubCli()
            >>> ctx = DotAgentContext.for_test(github_cli=github_cli, debug=True)
        """
        # Import here to avoid circular dependency with tests
        from tests.fakes.fake_github_cli import FakeDotAgentGitHubCli

        from erk.core.github.issues import FakeGitHubIssues

        # Provide defaults - ensures non-None values for type checker
        resolved_github_cli: DotAgentGitHubCli = (
            github_cli if github_cli is not None else FakeDotAgentGitHubCli()
        )
        resolved_github_issues: GitHubIssues = (
            github_issues if github_issues is not None else FakeGitHubIssues()
        )

        return DotAgentContext(
            github_cli=resolved_github_cli,
            github_issues=resolved_github_issues,
            debug=debug,
        )


def create_context(*, debug: bool) -> DotAgentContext:
    """Create production context with real implementations.

    This is the canonical factory for creating the application context.
    Called once at CLI entry point to create the context for the entire
    command execution.

    Args:
        debug: If True, enable debug mode (full stack traces in error handling)

    Returns:
        DotAgentContext with real GitHub integrations

    Example:
        >>> ctx = create_context(debug=False)
        >>> result = ctx.github_cli.create_issue(title, body, labels)
    """
    return DotAgentContext(
        github_cli=RealDotAgentGitHubCli(),
        github_issues=RealGitHubIssues(),
        debug=debug,
    )
