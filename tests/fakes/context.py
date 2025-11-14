"""Factory functions for creating test contexts."""

from pathlib import Path

from tests.fakes.completion_ops import FakeCompletionOps
from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from workstack.cli.config import LoadedConfig
from workstack.core.context import WorkstackContext
from workstack.core.global_config import GlobalConfig
from workstack.core.repo_discovery import NoRepoSentinel, RepoContext
from workstack.core.script_writer import ScriptWriterOps


def create_test_context(
    git_ops: FakeGitOps | None = None,
    github_ops: FakeGitHubOps | None = None,
    graphite_ops: FakeGraphiteOps | None = None,
    shell_ops: FakeShellOps | None = None,
    completion_ops: FakeCompletionOps | None = None,
    script_writer: ScriptWriterOps | None = None,
    cwd: Path | None = None,
    global_config: GlobalConfig | None = None,
    local_config: LoadedConfig | None = None,
    repo: RepoContext | NoRepoSentinel | None = None,
    dry_run: bool = False,
) -> WorkstackContext:
    """Create test context with optional pre-configured ops.

    This is a convenience wrapper around WorkstackContext.for_test() for backward
    compatibility. New code should use WorkstackContext.for_test() directly.

    Args:
        git_ops: Optional FakeGitOps with test configuration.
                If None, creates empty FakeGitOps.
        github_ops: Optional FakeGitHubOps with test configuration.
                   If None, creates empty FakeGitHubOps.
        graphite_ops: Optional FakeGraphiteOps with test configuration.
                     If None, creates empty FakeGraphiteOps.
        shell_ops: Optional FakeShellOps with test configuration.
                  If None, creates empty FakeShellOps (no shell detected).
        completion_ops: Optional FakeCompletionOps with test configuration.
                       If None, creates empty FakeCompletionOps.
        script_writer: Optional ScriptWriterOps (Real or Fake) for test context.
                      If None, defaults to FakeScriptWriterOps in WorkstackContext.for_test.
                      Pass RealScriptWriterOps() for integration tests that need real scripts.
        cwd: Optional current working directory path for test context.
            If None, defaults to Path("/test/default/cwd") to prevent accidental use
            of real Path.cwd() in tests.
        global_config: Optional GlobalConfig for test context.
                      If None, uses test defaults.
        local_config: Optional LoadedConfig for test context.
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
    return WorkstackContext.for_test(
        git_ops=git_ops,
        github_ops=github_ops,
        graphite_ops=graphite_ops,
        shell_ops=shell_ops,
        completion_ops=completion_ops,
        script_writer=script_writer,
        cwd=cwd,
        global_config=global_config,
        local_config=local_config,
        repo=repo,
        dry_run=dry_run,
    )
