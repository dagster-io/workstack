from pathlib import Path

from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext, discover_repo_or_sentinel


def discover_repo_context(ctx: ErkContext, start: Path) -> RepoContext:
    """Walk up from `start` to find a directory containing `.git`.

    Returns a RepoContext pointing to the repo root and the global worktrees directory
    for this repository.
    Raises FileNotFoundError if not inside a git repo.

    Note: Properly handles git worktrees by finding the main repository root,
    not the worktree's .git file.
    """
    if ctx.global_config is None:
        raise FileNotFoundError("Global config not found. Run 'erk init' to create it.")

    result = discover_repo_or_sentinel(start, ctx.global_config.erk_root, ctx.git)
    if isinstance(result, RepoContext):
        return result
    raise FileNotFoundError(result.message)


def worktree_path_for(worktrees_dir: Path, name: str) -> Path:
    """Return the absolute path for a named worktree within worktrees directory.

    Note: Does not handle 'root' as a special case. Commands that support
    'root' must check for it explicitly and use repo.root directly.

    Args:
        worktrees_dir: The directory containing all worktrees for this repo
        name: The worktree name (e.g., 'feature-a')

    Returns:
        Absolute path to the worktree (e.g., ~/.erk/repos/myrepo/worktrees/feature-a/)
    """
    return (worktrees_dir / name).resolve()


def validate_worktree_name_for_deletion(name: str) -> None:
    """Validate that a worktree name is safe for deletion.

    Rejects:
    - Empty strings
    - `.` or `..` (current/parent directory references)
    - `root` (explicit root worktree name)
    - Names starting with `/` (absolute paths)
    - Names containing `/` (path separators)

    Raises SystemExit(1) with error message if validation fails.
    """
    Ensure.not_empty(name.strip() if name else "", "Worktree name cannot be empty")
    Ensure.invariant(
        name not in (".", ".."),
        f"Cannot delete '{name}' - directory references not allowed",
    )
    Ensure.invariant(name != "root", "Cannot delete 'root' - root worktree name not allowed")
    Ensure.invariant(
        not name.startswith("/"),
        f"Cannot delete '{name}' - absolute paths not allowed",
    )
    Ensure.invariant("/" not in name, f"Cannot delete '{name}' - path separators not allowed")
