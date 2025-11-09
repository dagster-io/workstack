"""Application context with dependency injection."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

import tomlkit

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

    trunk_branch = read_trunk_from_pyproject(repo_root) if repo_root else None

    return WorkstackContext(
        git_ops=git_ops,
        global_config_ops=global_config_ops,
        github_ops=github_ops,
        graphite_ops=graphite_ops,
        shell_ops=RealShellOps(),
        cwd=Path.cwd(),
        dry_run=dry_run,
        trunk_branch=trunk_branch,
    )
