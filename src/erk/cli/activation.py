"""Shell activation script generation for worktree environments.

This module provides utilities for generating shell scripts that activate
worktree environments by setting up virtual environments and loading .env files.
"""

import shlex
from pathlib import Path


def render_activation_script(
    *,
    worktree_path: Path,
    final_message: str = 'echo "Activated worktree: $(pwd)"',
    comment: str = "work activate-script",
) -> str:
    """Return shell code that activates a worktree's venv and .env.

    The script:
      - cds into the worktree
      - creates .venv with `uv sync` if not present
      - sources `.venv/bin/activate` if present
      - exports variables from `.env` if present
    Works in bash and zsh.

    Args:
        worktree_path: Path to the worktree directory
        final_message: Shell command for final echo message (default shows activation)
        comment: Comment line for script identification (default: "work activate-script")

    Returns:
        Shell script as a string with newlines

    Example:
        >>> script = render_activation_script(
        ...     worktree_path=Path("/path/to/worktree"),
        ...     final_message='echo "Ready: $(pwd)"'
        ... )
    """
    wt = shlex.quote(str(worktree_path))
    venv_dir = shlex.quote(str(worktree_path / ".venv"))
    venv_activate = shlex.quote(str(worktree_path / ".venv" / "bin" / "activate"))

    return f"""# {comment}
cd {wt}
# Unset VIRTUAL_ENV to avoid conflicts with previous activations
unset VIRTUAL_ENV
# Create venv if it doesn't exist
if [ ! -d {venv_dir} ]; then
  echo 'Creating virtual environment with uv sync...'
  uv sync
fi
if [ -f {venv_activate} ]; then
  . {venv_activate}
fi
# Load .env into the environment (allexport)
set -a
if [ -f ./.env ]; then . ./.env; fi
set +a
# Optional: show where we are
{final_message}
"""
