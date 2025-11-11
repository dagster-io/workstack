"""Application context with dependency injection."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

import tomlkit

from workstack.cli.config import LoadedConfig, load_config
from workstack.core.completion_ops import CompletionOps, RealCompletionOps
from workstack.core.github_ops import DryRunGitHubOps, GitHubOps, RealGitHubOps
from workstack.core.gitops import DryRunGitOps, GitOps, RealGitOps
from workstack.core.global_config import (
    FilesystemGlobalConfigOps,
    GlobalConfig,
    GlobalConfigOps,
    InMemoryGlobalConfigOps,
)
from workstack.core.graphite_ops import DryRunGraphiteOps, GraphiteOps, RealGraphiteOps
from workstack.core.repo_discovery import (
    NoRepoSentinel,
    RepoContext,
    discover_repo_or_sentinel,
    ensure_workstacks_dir,
)
from workstack.core.shell_ops import RealShellOps, ShellOps


@dataclass(frozen=True)
class WorkstackContext:
    """Immutable context holding all dependencies for workstack operations.

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
    cwd: Path  # Current working directory at CLI invocation
    global_config: GlobalConfig | None
    local_config: LoadedConfig
    repo: RepoContext | NoRepoSentinel
    dry_run: bool
    trunk_branch: str | None

    @staticmethod
    def minimal(git_ops: GitOps, cwd: Path, dry_run: bool = False) -> "WorkstackContext":
        """Create minimal context with only git_ops configured, rest are test defaults.

        Useful for simple tests that only need git operations. Other ops
        are initialized with their standard test defaults (fake implementations).

        Args:
            git_ops: The GitOps implementation (usually FakeGitOps with test configuration)
            cwd: Current working directory path for the context
            dry_run: Whether to enable dry-run mode (default False)

        Returns:
            WorkstackContext with git_ops configured and other dependencies using test defaults

        Example:
            Before (7 lines):
            >>> from tests.fakes.gitops import FakeGitOps
            >>> from tests.fakes.github_ops import FakeGitHubOps
            >>> from tests.fakes.graphite_ops import FakeGraphiteOps
            >>> from tests.fakes.shell_ops import FakeShellOps
            >>> ctx = WorkstackContext(
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
            >>> ctx = WorkstackContext.minimal(git_ops, cwd)

        Note:
            For more complex test setup with custom configs or multiple ops,
            use WorkstackContext.for_test() instead.
        """
        from tests.fakes.completion_ops import FakeCompletionOps
        from tests.fakes.github_ops import FakeGitHubOps
        from tests.fakes.graphite_ops import FakeGraphiteOps
        from tests.fakes.shell_ops import FakeShellOps

        return WorkstackContext(
            git_ops=git_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            completion_ops=FakeCompletionOps(),
            global_config_ops=InMemoryGlobalConfigOps(config=None),
            cwd=cwd,
            global_config=None,
            local_config=LoadedConfig(env={}, post_create_commands=[], post_create_shell=None),
            repo=NoRepoSentinel(),
            dry_run=dry_run,
            trunk_branch=None,
        )

    @staticmethod
    def for_test(
        git_ops: GitOps | None = None,
        github_ops: GitHubOps | None = None,
        graphite_ops: GraphiteOps | None = None,
        shell_ops: ShellOps | None = None,
        completion_ops: CompletionOps | None = None,
        global_config_ops: GlobalConfigOps | None = None,
        cwd: Path | None = None,
        global_config: GlobalConfig | None = None,
        local_config: LoadedConfig | None = None,
        repo: RepoContext | NoRepoSentinel | None = None,
        dry_run: bool = False,
        trunk_branch: str | None = None,
    ) -> "WorkstackContext":
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
            cwd: Optional current working directory. If None, uses Path("/test/default/cwd").
            global_config: Optional GlobalConfig. If None, uses test defaults.
            local_config: Optional LoadedConfig. If None, uses empty defaults.
            repo: Optional RepoContext or NoRepoSentinel. If None, uses NoRepoSentinel().
            dry_run: Whether to enable dry-run mode (default False).
            trunk_branch: Optional trunk branch name. If None, no trunk configured.

        Returns:
            WorkstackContext configured with provided values and test defaults

        Example:
            Simple case (use .minimal() instead):
            >>> git_ops = FakeGitOps(default_branches={Path("/repo"): "main"})
            >>> ctx = WorkstackContext.for_test(git_ops=git_ops)

            Complex case with multiple ops:
            >>> git_ops = FakeGitOps(default_branches={Path("/repo"): "main"})
            >>> github_ops = FakeGitHubOps(prs={123: PR(...)})
            >>> graphite_ops = FakeGraphiteOps(stack_info={"feature": StackInfo(...)})
            >>> ctx = WorkstackContext.for_test(
            ...     git_ops=git_ops,
            ...     github_ops=github_ops,
            ...     graphite_ops=graphite_ops,
            ... )

        Note:
            For simple cases that only need git_ops, use WorkstackContext.minimal()
            which is more concise.
        """
        from tests.fakes.completion_ops import FakeCompletionOps
        from tests.fakes.github_ops import FakeGitHubOps
        from tests.fakes.gitops import FakeGitOps
        from tests.fakes.graphite_ops import FakeGraphiteOps
        from tests.fakes.shell_ops import FakeShellOps

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

        if global_config is None:
            global_config = GlobalConfig(
                workstacks_root=Path("/test/workstacks"),
                use_graphite=False,
                shell_setup_complete=False,
                show_pr_info=True,
                show_pr_checks=False,
            )

        if global_config_ops is None:
            global_config_ops = InMemoryGlobalConfigOps(config=global_config)

        if local_config is None:
            local_config = LoadedConfig(env={}, post_create_commands=[], post_create_shell=None)

        if repo is None:
            repo = NoRepoSentinel()

        return WorkstackContext(
            git_ops=git_ops,
            github_ops=github_ops,
            graphite_ops=graphite_ops,
            shell_ops=shell_ops,
            completion_ops=completion_ops,
            global_config_ops=global_config_ops,
            cwd=cwd or Path("/test/default/cwd"),
            global_config=global_config,
            local_config=local_config,
            repo=repo,
            dry_run=dry_run,
            trunk_branch=trunk_branch,
        )


def read_trunk_from_pyproject(repo_root: Path) -> str | None:
    """Read trunk branch configuration from pyproject.toml.

    Args:
        repo_root: Path to the repository root directory

    Returns:
        Configured trunk branch name, or None if not configured
    """
    pyproject_path = repo_root / "pyproject.toml"

    if not pyproject_path.exists():
        return None

    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    tool_section = data.get("tool")
    if tool_section is None:
        return None

    workstack_section = tool_section.get("workstack")
    if workstack_section is None:
        return None

    return workstack_section.get("trunk_branch")


def write_trunk_to_pyproject(repo_root: Path, trunk: str) -> None:
    """Write trunk branch configuration to pyproject.toml.

    Creates or updates the [tool.workstack] section with trunk_branch setting.
    Preserves existing formatting and comments using tomlkit.

    Args:
        repo_root: Path to the repository root directory
        trunk: Trunk branch name to configure
    """
    pyproject_path = repo_root / "pyproject.toml"

    # Load existing file or create new document
    if pyproject_path.exists():
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


def create_context(*, dry_run: bool, repo_root: Path | None = None) -> WorkstackContext:
    """Create production context with real implementations.

    Called at CLI entry point to create the context for the entire
    command execution.

    Args:
        dry_run: If True, wrap all dependencies with dry-run wrappers that
                 print intended actions without executing them
        repo_root: Optional path to repository root for reading trunk configuration.
                   If None, trunk_branch will be None (to be determined later).

    Returns:
        WorkstackContext with real implementations, wrapped in dry-run
        wrappers if dry_run=True

    Example:
        >>> ctx = create_context(dry_run=False)
        >>> worktrees = ctx.git_ops.list_worktrees(Path("/repo"))
        >>> workstacks_root = ctx.global_config.workstacks_root
    """
    # 1. Capture cwd (no deps)
    cwd = Path.cwd()

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
    workstacks_root = global_config.workstacks_root if global_config else Path.home() / "worktrees"
    repo = discover_repo_or_sentinel(cwd, workstacks_root, git_ops)

    # 6. Load local config (or defaults if no repo)
    if isinstance(repo, NoRepoSentinel):
        local_config = LoadedConfig(env={}, post_create_commands=[], post_create_shell=None)
    else:
        workstacks_dir = ensure_workstacks_dir(repo)
        local_config = load_config(workstacks_dir)

    # 7. Apply dry-run wrappers if needed
    if dry_run:
        git_ops = DryRunGitOps(git_ops)
        graphite_ops = DryRunGraphiteOps(graphite_ops)
        github_ops = DryRunGitHubOps(github_ops)

    # 8. Load trunk branch config if in a repo
    trunk_branch = read_trunk_from_pyproject(repo_root) if repo_root else None

    # 9. Create context with all values
    return WorkstackContext(
        git_ops=git_ops,
        github_ops=github_ops,
        graphite_ops=graphite_ops,
        shell_ops=RealShellOps(),
        completion_ops=RealCompletionOps(),
        global_config_ops=FilesystemGlobalConfigOps(),
        cwd=cwd,
        global_config=global_config,
        local_config=local_config,
        repo=repo,
        dry_run=dry_run,
        trunk_branch=trunk_branch,
    )


def regenerate_context(
    existing_ctx: WorkstackContext, *, repo_root: Path | None = None
) -> WorkstackContext:
    """Regenerate context with fresh cwd and trunk_branch.

    Creates a new WorkstackContext with:
    - Current working directory (Path.cwd())
    - Fresh trunk_branch from pyproject.toml (if repo_root provided)
    - Preserved dry_run state and operation instances

    Use this after mutations like os.chdir() or worktree removal
    to ensure ctx.cwd reflects actual current directory.

    Args:
        existing_ctx: Current context to preserve settings from
        repo_root: Optional path to repo for trunk_branch lookup.
                   If None, trunk_branch will be None.

    Returns:
        New WorkstackContext with regenerated state

    Example:
        # After os.chdir() or worktree removal
        repo = discover_repo_context(ctx, Path.cwd())
        ctx = regenerate_context(ctx, repo_root=repo.root)
    """
    return create_context(dry_run=existing_ctx.dry_run, repo_root=repo_root)
