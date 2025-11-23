"""Helper functions for accessing context dependencies with LBYL checks.

This module provides getter functions that encapsulate the "Look Before You Leap"
pattern for accessing dependencies from the DotAgentContext. These functions:

1. Check that context is initialized
2. Return the typed dependency
3. Exit with clear error message if context is missing

This eliminates code duplication across kit CLI commands.
"""

from pathlib import Path

import click
from erk_shared.github.issues import GitHubIssues


def require_github_issues(ctx: click.Context) -> GitHubIssues:
    """Get GitHub Issues from context, exiting with error if not initialized.

    Uses LBYL pattern to check context before accessing. If context is not
    initialized (ctx.obj is None), prints error to stderr and exits with code 1.

    Args:
        ctx: Click context (must have DotAgentContext in ctx.obj)

    Returns:
        GitHubIssues instance from context

    Raises:
        SystemExit: If context not initialized (exits with code 1)

    Example:
        >>> @click.command()
        >>> @click.pass_context
        >>> def my_command(ctx: click.Context) -> None:
        ...     github = require_github_issues(ctx)
        ...     github.add_comment(repo_root, issue_number, body)
    """
    if ctx.obj is None:
        click.echo("Error: Context not initialized", err=True)
        raise SystemExit(1)

    return ctx.obj.github_issues


def require_repo_root(ctx: click.Context) -> Path:
    """Get repo root from context, exiting with error if not initialized.

    Uses LBYL pattern to check context before accessing.

    Args:
        ctx: Click context (must have DotAgentContext in ctx.obj)

    Returns:
        Path to repository root

    Raises:
        SystemExit: If context not initialized (exits with code 1)

    Example:
        >>> @click.command()
        >>> @click.pass_context
        >>> def my_command(ctx: click.Context) -> None:
        ...     repo_root = require_repo_root(ctx)
        ...     github = require_github_issues(ctx)
        ...     github.create_issue(repo_root, title, body, labels)
    """
    if ctx.obj is None:
        click.echo("Error: Context not initialized", err=True)
        raise SystemExit(1)

    return ctx.obj.repo_root
