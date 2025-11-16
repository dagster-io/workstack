from pathlib import Path

from erk.cli.output import user_output
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

    result = discover_repo_or_sentinel(start, ctx.global_config.workstacks_root, ctx.git_ops)
    if isinstance(result, RepoContext):
        return result
    raise FileNotFoundError(result.message)


def worktree_path_for(workstacks_dir: Path, name: str) -> Path:
    """Return the absolute path for a named worktree within workstacks_dir.

    Note: Does not handle 'root' as a special case. Commands that support
    'root' must check for it explicitly and use repo.root directly.

    Args:
        workstacks_dir: The directory containing all workstacks for this repo
        name: The worktree name (e.g., 'feature-a')

    Returns:
        Absolute path to the worktree (e.g., ~/worktrees/myrepo/feature-a/)
    """
    return (workstacks_dir / name).resolve()


def validate_worktree_name_for_removal(name: str) -> None:
    """Validate that a worktree name is safe for removal.

    Rejects:
    - Empty strings
    - `.` or `..` (current/parent directory references)
    - `root` (explicit root worktree name)
    - Names starting with `/` (absolute paths)
    - Names containing `/` (path separators)

    Raises SystemExit(1) with error message if validation fails.
    """
    if not name or not name.strip():
        user_output("Error: Worktree name cannot be empty")
        raise SystemExit(1)

    if name in (".", ".."):
        user_output(f"Error: Cannot remove '{name}' - directory references not allowed")
        raise SystemExit(1)

    if name == "root":
        user_output("Error: Cannot remove 'root' - root worktree name not allowed")
        raise SystemExit(1)

    if name.startswith("/"):
        user_output(f"Error: Cannot remove '{name}' - absolute paths not allowed")
        raise SystemExit(1)

    if "/" in name:
        user_output(f"Error: Cannot remove '{name}' - path separators not allowed")
        raise SystemExit(1)
