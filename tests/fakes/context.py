"""Factory functions for creating test contexts."""

from pathlib import Path

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.global_config_ops import FakeGlobalConfigOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from workstack.core.context import WorkstackContext


def create_test_context(
    git_ops: FakeGitOps | None = None,
    global_config_ops: FakeGlobalConfigOps | None = None,
    github_ops: FakeGitHubOps | None = None,
    graphite_ops: FakeGraphiteOps | None = None,
    shell_ops: FakeShellOps | None = None,
    cwd: Path | None = None,
    dry_run: bool = False,
) -> WorkstackContext:
    """Create test context with optional pre-configured ops.

    Args:
        git_ops: Optional FakeGitOps with test configuration.
                If None, creates empty FakeGitOps.
        global_config_ops: Optional FakeGlobalConfigOps with test configuration.
                          If None, creates FakeGlobalConfigOps with no config (doesn't exist).
        github_ops: Optional FakeGitHubOps with test configuration.
                   If None, creates empty FakeGitHubOps.
        graphite_ops: Optional FakeGraphiteOps with test configuration.
                     If None, creates empty FakeGraphiteOps.
        shell_ops: Optional FakeShellOps with test configuration.
                  If None, creates empty FakeShellOps (no shell detected).
        cwd: Optional current working directory path for test context.
            If None, defaults to Path("/test/default/cwd") to prevent accidental use
            of real Path.cwd() in tests.
        dry_run: Whether to set dry_run mode

    Returns:
        Frozen WorkstackContext for use in tests

    Example:
        # With pre-configured git ops
        >>> git_ops = FakeGitOps(default_branches={Path("/repo"): "main"})
        >>> ctx = create_test_context(git_ops=git_ops)

        # With pre-configured global config
        >>> from workstack.cli.config import GlobalConfig
        >>> config_ops = FakeGlobalConfigOps(
        ...     config=GlobalConfig(
        ...         workstacks_root=Path("/tmp/workstacks"),
        ...         use_graphite=False,
        ...         shell_setup_complete=False,
        ...     )
        ... )
        >>> ctx = create_test_context(global_config_ops=config_ops)

        # Without any ops (empty fakes)
        >>> ctx = create_test_context()
    """
    if git_ops is None:
        git_ops = FakeGitOps()

    if global_config_ops is None:
        global_config_ops = FakeGlobalConfigOps()

    if github_ops is None:
        github_ops = FakeGitHubOps()

    if graphite_ops is None:
        graphite_ops = FakeGraphiteOps()

    if shell_ops is None:
        shell_ops = FakeShellOps()

    return WorkstackContext(
        git_ops=git_ops,
        global_config_ops=global_config_ops,
        github_ops=github_ops,
        graphite_ops=graphite_ops,
        shell_ops=shell_ops,
        cwd=cwd or Path("/test/default/cwd"),
        dry_run=dry_run,
    )
