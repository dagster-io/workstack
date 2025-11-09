"""Application context with dependency injection."""

from dataclasses import dataclass
from pathlib import Path

from workstack.core.github_ops import DryRunGitHubOps, GitHubOps, RealGitHubOps
from workstack.core.gitops import DryRunGitOps, GitOps, RealGitOps
from workstack.core.global_config_ops import (
    DryRunGlobalConfigOps,
    GlobalConfigOps,
    RealGlobalConfigOps,
)
from workstack.core.graphite_ops import DryRunGraphiteOps, GraphiteOps, RealGraphiteOps
from workstack.core.shell_ops import RealShellOps, ShellOps


@dataclass(frozen=True)
class WorkstackContext:
    """Immutable context holding all dependencies for workstack operations.

    Created at CLI entry point and threaded through the application.
    Frozen to prevent accidental modification at runtime.
    """

    git_ops: GitOps
    global_config_ops: GlobalConfigOps
    github_ops: GitHubOps
    graphite_ops: GraphiteOps
    shell_ops: ShellOps
    cwd: Path  # Current working directory at CLI invocation
    dry_run: bool


def create_context(*, dry_run: bool) -> WorkstackContext:
    """Create production context with real implementations.

    Called at CLI entry point to create the context for the entire
    command execution.

    Args:
        dry_run: If True, wrap all dependencies with dry-run wrappers that
                 print intended actions without executing them

    Returns:
        WorkstackContext with real implementations, wrapped in dry-run
        wrappers if dry_run=True

    Example:
        >>> ctx = create_context(dry_run=False)
        >>> worktrees = ctx.git_ops.list_worktrees(Path("/repo"))
        >>> workstacks_root = ctx.global_config_ops.get_workstacks_root()
    """
    git_ops: GitOps = RealGitOps()
    graphite_ops: GraphiteOps = RealGraphiteOps()
    github_ops: GitHubOps = RealGitHubOps()
    global_config_ops: GlobalConfigOps = RealGlobalConfigOps()

    if dry_run:
        git_ops = DryRunGitOps(git_ops)
        graphite_ops = DryRunGraphiteOps(graphite_ops)
        github_ops = DryRunGitHubOps(github_ops)
        global_config_ops = DryRunGlobalConfigOps(global_config_ops)

    return WorkstackContext(
        git_ops=git_ops,
        global_config_ops=global_config_ops,
        github_ops=github_ops,
        graphite_ops=graphite_ops,
        shell_ops=RealShellOps(),
        cwd=Path.cwd(),
        dry_run=dry_run,
    )
