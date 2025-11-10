"""Application context with dependency injection."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

import tomlkit

from workstack.cli.config import LoadedConfig, load_config
from workstack.core.github_ops import DryRunGitHubOps, GitHubOps, RealGitHubOps
from workstack.core.gitops import DryRunGitOps, GitOps, RealGitOps
from workstack.core.global_config import GlobalConfig, load_global_config
from workstack.core.graphite_ops import DryRunGraphiteOps, GraphiteOps, RealGraphiteOps
from workstack.core.repo_discovery import (
    NoRepoSentinel,
    RepoContext,
    discover_repo_or_sentinel,
    ensure_workstacks_dir,
)
from workstack.core.shell_ops import RealShellOps, ShellOps


class GlobalConfigNotFound:
    """Sentinel value indicating global config file was not found."""

    pass


@dataclass(frozen=True)
class WorkstackContext:
    """Immutable context holding all dependencies for workstack operations.

    Created at CLI entry point and threaded through the application.
    Frozen to prevent accidental modification at runtime.

    Note: global_config is either a valid GlobalConfig or GlobalConfigNotFound.
    Use isinstance(ctx.global_config, GlobalConfigNotFound) to check if config is missing.
    """

    git_ops: GitOps
    github_ops: GitHubOps
    graphite_ops: GraphiteOps
    shell_ops: ShellOps
    cwd: Path  # Current working directory at CLI invocation
    global_config: GlobalConfig | GlobalConfigNotFound
    repo_config: LoadedConfig
    repo: RepoContext | NoRepoSentinel
    dry_run: bool
    trunk_branch: str | None


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

    # 2. Load global config (no deps) - sentinel if not exists (for init command)
    from workstack.core.global_config import global_config_exists

    global_config: GlobalConfig | GlobalConfigNotFound
    if global_config_exists():
        global_config = load_global_config()
    else:
        # For init command only: config doesn't exist yet
        global_config = GlobalConfigNotFound()

    # 3. Create ops (need git_ops for repo discovery)
    git_ops: GitOps = RealGitOps()
    graphite_ops: GraphiteOps = RealGraphiteOps()
    github_ops: GitHubOps = RealGitHubOps()

    # 4. Discover repo (only needs cwd, workstacks_root, git_ops)
    # If global_config is sentinel, skip repo discovery (only init command should work)
    if isinstance(global_config, GlobalConfigNotFound):
        repo = NoRepoSentinel(message="Global config not found - run 'workstack init' first")
    else:
        repo = discover_repo_or_sentinel(cwd, global_config.workstacks_root, git_ops)

    # 5. Load repo config (or defaults if no repo)
    if isinstance(repo, NoRepoSentinel):
        repo_config = LoadedConfig(env={}, post_create_commands=[], post_create_shell=None)
    else:
        workstacks_dir = ensure_workstacks_dir(repo)
        repo_config = load_config(workstacks_dir)

    # 6. Apply dry-run wrappers if needed
    if dry_run:
        git_ops = DryRunGitOps(git_ops)
        graphite_ops = DryRunGraphiteOps(graphite_ops)
        github_ops = DryRunGitHubOps(github_ops)

    # 7. Load trunk branch config if in a repo
    trunk_branch = read_trunk_from_pyproject(repo_root) if repo_root else None

    # 8. Create context with all values
    return WorkstackContext(
        git_ops=git_ops,
        github_ops=github_ops,
        graphite_ops=graphite_ops,
        shell_ops=RealShellOps(),
        cwd=cwd,
        global_config=global_config,
        repo_config=repo_config,
        repo=repo,
        dry_run=dry_run,
        trunk_branch=trunk_branch,
    )
