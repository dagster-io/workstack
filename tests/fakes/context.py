"""Factory functions for creating test contexts."""

from pathlib import Path

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from workstack.cli.config import LoadedConfig
from workstack.core.context import WorkstackContext
from workstack.core.global_config import GlobalConfig
from workstack.core.repo_discovery import NoRepoSentinel, RepoContext


def create_test_context(
    git_ops: FakeGitOps | None = None,
    github_ops: FakeGitHubOps | None = None,
    graphite_ops: FakeGraphiteOps | None = None,
    shell_ops: FakeShellOps | None = None,
    cwd: Path | None = None,
    global_config: GlobalConfig | None = None,
    repo_config: LoadedConfig | None = None,
    repo: RepoContext | NoRepoSentinel | None = None,
    dry_run: bool = False,
) -> WorkstackContext:
    """Create test context with optional pre-configured ops.

    Args:
        git_ops: Optional FakeGitOps with test configuration.
                If None, creates empty FakeGitOps.
        github_ops: Optional FakeGitHubOps with test configuration.
                   If None, creates empty FakeGitHubOps.
        graphite_ops: Optional FakeGraphiteOps with test configuration.
                     If None, creates empty FakeGraphiteOps.
        shell_ops: Optional FakeShellOps with test configuration.
                  If None, creates empty FakeShellOps (no shell detected).
        cwd: Optional current working directory path for test context.
            If None, defaults to Path("/test/default/cwd") to prevent accidental use
            of real Path.cwd() in tests.
        global_config: Optional GlobalConfig for test context.
                      If None, uses test defaults.
        repo_config: Optional LoadedConfig for test context.
                    If None, uses empty defaults.
        repo: Optional RepoContext or NoRepoSentinel for test context.
             If None, uses NoRepoSentinel().
        dry_run: Whether to set dry_run mode

    Returns:
        Frozen WorkstackContext for use in tests

    Example:
        # With pre-configured git ops
        >>> git_ops = FakeGitOps(default_branches={Path("/repo"): "main"})
        >>> ctx = create_test_context(git_ops=git_ops)

        # With pre-configured global config
        >>> from workstack.core.global_config import GlobalConfig
        >>> config = GlobalConfig(
        ...     workstacks_root=Path("/tmp/workstacks"),
        ...     use_graphite=False,
        ...     shell_setup_complete=False,
        ...     show_pr_info=True,
        ...     show_pr_checks=False,
        ... )
        >>> ctx = create_test_context(global_config=config)

        # Without any ops (empty fakes)
        >>> ctx = create_test_context()
    """
    if git_ops is None:
        git_ops = FakeGitOps()

    if github_ops is None:
        github_ops = FakeGitHubOps()

    if graphite_ops is None:
        graphite_ops = FakeGraphiteOps()

    if shell_ops is None:
        shell_ops = FakeShellOps()

    if global_config is None:
        global_config = GlobalConfig(
            workstacks_root=Path("/test/workstacks"),
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

    if repo_config is None:
        repo_config = LoadedConfig(env={}, post_create_commands=[], post_create_shell=None)

    if repo is None:
        repo = NoRepoSentinel()

    return WorkstackContext(
        git_ops=git_ops,
        github_ops=github_ops,
        graphite_ops=graphite_ops,
        shell_ops=shell_ops,
        cwd=cwd or Path("/test/default/cwd"),
        global_config=global_config,
        repo_config=repo_config,
        repo=repo,
        dry_run=dry_run,
    )
