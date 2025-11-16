"""Application context with dependency injection."""

from dataclasses import dataclass
from pathlib import Path

import click
import tomlkit

from erk.cli.config import LoadedConfig, load_config
from erk.cli.output import user_output
from erk.core.completion_ops import CompletionOps, RealCompletionOps
from erk.core.github_ops import GitHubOps, NoopGitHubOps, RealGitHubOps
from erk.core.gitops import GitOps, NoopGitOps, RealGitOps
from erk.core.global_config import (
    FilesystemGlobalConfigOps,
    GlobalConfig,
    GlobalConfigOps,
    InMemoryGlobalConfigOps,
)
from erk.core.graphite_ops import GraphiteOps, NoopGraphiteOps, RealGraphiteOps
from erk.core.repo_discovery import (
    NoRepoSentinel,
    RepoContext,
    discover_repo_or_sentinel,
    ensure_repo_dir,
)
from erk.core.script_writer import RealScriptWriterOps, ScriptWriterOps
from erk.core.shell_ops import RealShellOps, ShellOps


@dataclass(frozen=True)
class ErkContext:
    """Immutable context holding all dependencies for erk operations.

    Created at CLI entry point and threaded through the application.
    Frozen to prevent accidental modification at runtime.

    Note: global_config may be None only during init command before config is created.
    All other commands should have a valid GlobalConfig.
    """

    git_ops: GitOps
    github_ops: GitHubOps
    graphite_ops: GraphiteOps
    shell_ops: ShellOps
    completion_ops: CompletionOps
    global_config_ops: GlobalConfigOps
    script_writer: ScriptWriterOps
    cwd: Path  # Current working directory at CLI invocation
    global_config: GlobalConfig | None
    local_config: LoadedConfig
    repo: RepoContext | NoRepoSentinel
    dry_run: bool

    @property
    def trunk_branch(self) -> str | None:
        """Get the trunk branch name from git detection.

        Returns None if not in a repository, otherwise uses git_ops to detect trunk.
        """
        if isinstance(self.repo, NoRepoSentinel):
            return None
        return self.git_ops.get_trunk_branch(self.repo.root)

    @staticmethod
    def minimal(git_ops: GitOps, cwd: Path, dry_run: bool = False) -> "ErkContext":
        """Create minimal context with only git_ops configured, rest are test defaults.

        Useful for simple tests that only need git operations. Other ops
        are initialized with their standard test defaults (fake implementations).

        Args:
            git_ops: The GitOps implementation (usually FakeGitOps with test configuration)
            cwd: Current working directory path for the context
            dry_run: Whether to enable dry-run mode (default False)

        Returns:
            ErkContext with git_ops configured and other dependencies using test defaults

        Example:
            Before (7 lines):
            >>> from tests.fakes.gitops import FakeGitOps
            >>> from tests.fakes.github_ops import FakeGitHubOps
            >>> from tests.fakes.graphite_ops import FakeGraphiteOps
            >>> from tests.fakes.shell_ops import FakeShellOps
            >>> ctx = ErkContext(
            ...     git_ops=git_ops,
            ...     github_ops=FakeGitHubOps(),
            ...     graphite_ops=FakeGraphiteOps(),
            ...     shell_ops=FakeShellOps(),
            ...     cwd=cwd,
            ...     global_config=None,
            ...     local_config=LoadedConfig(
            ...         env={}, post_create_commands=[], post_create_shell=None
            ...     ),
            ...     repo=NoRepoSentinel(),
            ...     dry_run=False,
            ...     trunk_branch=None,
            ... )

            After (1 line):
            >>> ctx = ErkContext.minimal(git_ops, cwd)

        Note:
            For more complex test setup with custom configs or multiple ops,
            use ErkContext.for_test() instead.
        """
        from tests.fakes.completion_ops import FakeCompletionOps
        from tests.fakes.github_ops import FakeGitHubOps
        from tests.fakes.graphite_ops import FakeGraphiteOps
        from tests.fakes.script_writer import FakeScriptWriterOps
        from tests.fakes.shell_ops import FakeShellOps

        return ErkContext(
            git_ops=git_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            completion_ops=FakeCompletionOps(),
            global_config_ops=InMemoryGlobalConfigOps(config=None),
            script_writer=FakeScriptWriterOps(),
            cwd=cwd,
            global_config=None,
            local_config=LoadedConfig(env={}, post_create_commands=[], post_create_shell=None),
            repo=NoRepoSentinel(),
            dry_run=dry_run,
        )

    @staticmethod
    def for_test(
        git_ops: GitOps | None = None,
        github_ops: GitHubOps | None = None,
        graphite_ops: GraphiteOps | None = None,
        shell_ops: ShellOps | None = None,
        completion_ops: CompletionOps | None = None,
        global_config_ops: GlobalConfigOps | None = None,
        script_writer: ScriptWriterOps | None = None,
        cwd: Path | None = None,
        global_config: GlobalConfig | None = None,
        local_config: LoadedConfig | None = None,
        repo: RepoContext | NoRepoSentinel | None = None,
        dry_run: bool = False,
    ) -> "ErkContext":
        """Create test context with optional pre-configured ops.

        Provides full control over all context parameters with sensible test defaults
        for any unspecified values. Use this for complex test scenarios that need
        specific configurations for multiple operations.

        Args:
            git_ops: Optional GitOps implementation. If None, creates empty FakeGitOps.
            github_ops: Optional GitHubOps implementation. If None, creates empty FakeGitHubOps.
            graphite_ops: Optional GraphiteOps implementation.
                         If None, creates empty FakeGraphiteOps.
            shell_ops: Optional ShellOps implementation. If None, creates empty FakeShellOps.
            completion_ops: Optional CompletionOps implementation.
                           If None, creates empty FakeCompletionOps.
            global_config_ops: Optional GlobalConfigOps implementation.
                              If None, creates InMemoryGlobalConfigOps with test config.
            script_writer: Optional ScriptWriterOps implementation.
                          If None, creates empty FakeScriptWriterOps.
            cwd: Optional current working directory. If None, uses Path("/test/default/cwd").
            global_config: Optional GlobalConfig. If None, uses test defaults.
            local_config: Optional LoadedConfig. If None, uses empty defaults.
            repo: Optional RepoContext or NoRepoSentinel. If None, uses NoRepoSentinel().
            dry_run: Whether to enable dry-run mode (default False).

        Returns:
            ErkContext configured with provided values and test defaults

        Example:
            Simple case (use .minimal() instead):
            >>> git_ops = FakeGitOps(default_branches={Path("/repo"): "main"})
            >>> ctx = ErkContext.for_test(git_ops=git_ops)

            Complex case with multiple ops:
            >>> git_ops = FakeGitOps(default_branches={Path("/repo"): "main"})
            >>> github_ops = FakeGitHubOps(prs={123: PR(...)})
            >>> graphite_ops = FakeGraphiteOps(stack_info={"feature": StackInfo(...)})
            >>> ctx = ErkContext.for_test(
            ...     git_ops=git_ops,
            ...     github_ops=github_ops,
            ...     graphite_ops=graphite_ops,
            ... )

        Note:
            For simple cases that only need git_ops, use ErkContext.minimal()
            which is more concise.
        """
        from tests.fakes.completion_ops import FakeCompletionOps
        from tests.fakes.github_ops import FakeGitHubOps
        from tests.fakes.gitops import FakeGitOps
        from tests.fakes.graphite_ops import FakeGraphiteOps
        from tests.fakes.script_writer import FakeScriptWriterOps
        from tests.fakes.shell_ops import FakeShellOps
        from tests.test_utils import sentinel_path

        if git_ops is None:
            git_ops = FakeGitOps()

        if github_ops is None:
            github_ops = FakeGitHubOps()

        if graphite_ops is None:
            graphite_ops = FakeGraphiteOps()

        if shell_ops is None:
            shell_ops = FakeShellOps()

        if completion_ops is None:
            completion_ops = FakeCompletionOps()

        if script_writer is None:
            script_writer = FakeScriptWriterOps()

        if global_config is None:
            global_config = GlobalConfig(
                erk_root=Path("/test/workstacks"),
                use_graphite=False,
                shell_setup_complete=False,
                show_pr_info=True,
            )

        if global_config_ops is None:
            global_config_ops = InMemoryGlobalConfigOps(config=global_config)

        if local_config is None:
            local_config = LoadedConfig(env={}, post_create_commands=[], post_create_shell=None)

        if repo is None:
            repo = NoRepoSentinel()

        # Apply dry-run wrappers if needed (matching production behavior)
        if dry_run:
            git_ops = NoopGitOps(git_ops)
            graphite_ops = NoopGraphiteOps(graphite_ops)
            github_ops = NoopGitHubOps(github_ops)

        return ErkContext(
            git_ops=git_ops,
            github_ops=github_ops,
            graphite_ops=graphite_ops,
            shell_ops=shell_ops,
            completion_ops=completion_ops,
            global_config_ops=global_config_ops,
            script_writer=script_writer,
            cwd=cwd or sentinel_path(),
            global_config=global_config,
            local_config=local_config,
            repo=repo,
            dry_run=dry_run,
        )


def write_trunk_to_pyproject(repo_root: Path, trunk: str, git_ops: GitOps | None = None) -> None:
    """Write trunk branch configuration to pyproject.toml.

    Creates or updates the [tool.workstack] section with trunk_branch setting.
    Preserves existing formatting and comments using tomlkit.

    Args:
        repo_root: Path to the repository root directory
        trunk: Trunk branch name to configure
        git_ops: Optional GitOps interface for path checking (uses .exists() if None)
    """
    pyproject_path = repo_root / "pyproject.toml"

    # Check existence using git_ops if available (for test compatibility)
    if git_ops is not None:
        path_exists = git_ops.path_exists(pyproject_path)
    else:
        path_exists = pyproject_path.exists()

    # Load existing file or create new document
    if path_exists:
        with pyproject_path.open("r", encoding="utf-8") as f:
            doc = tomlkit.load(f)
    else:
        doc = tomlkit.document()

    # Ensure [tool] section exists
    if "tool" not in doc:
        doc["tool"] = tomlkit.table()  # type: ignore[index]

    # Ensure [tool.workstack] section exists
    if "workstack" not in doc["tool"]:  # type: ignore[operator]
        doc["tool"]["workstack"] = tomlkit.table()  # type: ignore[index]

    # Set trunk_branch value
    doc["tool"]["workstack"]["trunk_branch"] = trunk  # type: ignore[index]

    # Write back to file
    with pyproject_path.open("w", encoding="utf-8") as f:
        tomlkit.dump(doc, f)


def safe_cwd() -> tuple[Path | None, str | None]:
    """Get current working directory, detecting if it no longer exists.

    Uses LBYL approach: checks if the operation will succeed before attempting it.

    Returns:
        tuple[Path | None, str | None]: (path, error_message)
        - If successful: (Path, None)
        - If directory deleted: (None, error_message)

    Note:
        This is an acceptable use of try/except since we're wrapping a third-party
        API (Path.cwd()) that provides no way to check the condition first.
    """
    try:
        cwd_path = Path.cwd()
        return (cwd_path, None)
    except (FileNotFoundError, OSError):
        return (
            None,
            "Current working directory no longer exists",
        )


def create_context(*, dry_run: bool) -> ErkContext:
    """Create production context with real implementations.

    Called at CLI entry point to create the context for the entire
    command execution.

    Args:
        dry_run: If True, wrap all dependencies with dry-run wrappers that
                 print intended actions without executing them

    Returns:
        ErkContext with real implementations, wrapped in dry-run
        wrappers if dry_run=True

    Example:
        >>> ctx = create_context(dry_run=False)
        >>> worktrees = ctx.git_ops.list_worktrees(Path("/repo"))
        >>> erk_root = ctx.global_config.erk_root
    """
    # 1. Capture cwd (no deps)
    cwd_result, error_msg = safe_cwd()
    if cwd_result is None:
        assert error_msg is not None
        # Emit clear error and exit
        user_output(click.style("Error: ", fg="red") + error_msg)
        user_output("\nThe directory you're running from has been deleted.")
        user_output("Please change to a valid directory and try again.")
        raise SystemExit(1)

    cwd = cwd_result

    # 2. Create global config ops
    global_config_ops = FilesystemGlobalConfigOps()

    # 3. Load global config (no deps) - None if not exists (for init command)
    global_config: GlobalConfig | None
    if global_config_ops.exists():
        global_config = global_config_ops.load()
    else:
        # For init command only: config doesn't exist yet
        global_config = None

    # 4. Create ops (need git_ops for repo discovery)
    git_ops: GitOps = RealGitOps()
    graphite_ops: GraphiteOps = RealGraphiteOps()
    github_ops: GitHubOps = RealGitHubOps()

    # 5. Discover repo (only needs cwd, workstacks_root, git_ops)
    # If global_config is None, use placeholder path for repo discovery
    erk_root = global_config.erk_root if global_config else Path.home() / "worktrees"
    repo = discover_repo_or_sentinel(cwd, erk_root, git_ops)

    # 6. Load local config (or defaults if no repo)
    if isinstance(repo, NoRepoSentinel):
        local_config = LoadedConfig(env={}, post_create_commands=[], post_create_shell=None)
    else:
        repo_dir = ensure_repo_dir(repo)
        local_config = load_config(repo_dir)

    # 7. Apply dry-run wrappers if needed
    if dry_run:
        git_ops = NoopGitOps(git_ops)
        graphite_ops = NoopGraphiteOps(graphite_ops)
        github_ops = NoopGitHubOps(github_ops)

    # 8. Create context with all values
    return ErkContext(
        git_ops=git_ops,
        github_ops=github_ops,
        graphite_ops=graphite_ops,
        shell_ops=RealShellOps(),
        completion_ops=RealCompletionOps(),
        global_config_ops=FilesystemGlobalConfigOps(),
        script_writer=RealScriptWriterOps(),
        cwd=cwd,
        global_config=global_config,
        local_config=local_config,
        repo=repo,
        dry_run=dry_run,
    )


def regenerate_context(existing_ctx: ErkContext) -> ErkContext:
    """Regenerate context with fresh cwd.

    Creates a new ErkContext with:
    - Current working directory (Path.cwd())
    - Preserved dry_run state and operation instances

    Use this after mutations like os.chdir() or worktree removal
    to ensure ctx.cwd reflects actual current directory.

    Args:
        existing_ctx: Current context to preserve settings from

    Returns:
        New ErkContext with regenerated state

    Example:
        # After os.chdir() or worktree removal
        ctx = regenerate_context(ctx)
    """
    return create_context(dry_run=existing_ctx.dry_run)
