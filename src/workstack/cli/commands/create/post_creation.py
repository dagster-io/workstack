"""Post-creation operations for the create command.

This module handles operations that occur after worktree creation:
- Writing .env files with configuration
- Running post-create commands
- Environment variable templating
"""

import shlex
from collections.abc import Iterable, Mapping
from pathlib import Path

from workstack.cli.config import LoadedConfig
from workstack.cli.subprocess_utils import run_with_error_reporting

from .types import WorktreeTarget


def write_env_file(target: WorktreeTarget, cfg: LoadedConfig) -> None:
    """Write .env file to worktree.

    Creates a .env file in the new worktree with templated environment
    variables from configuration.

    Args:
        target: Worktree target configuration
        cfg: Loaded configuration containing env templates
    """
    env_content = make_env_content(
        cfg, worktree_path=target.path, repo_root=target.repo_root, name=target.name
    )
    (target.path / ".env").write_text(env_content, encoding="utf-8")


def make_env_content(cfg: LoadedConfig, *, worktree_path: Path, repo_root: Path, name: str) -> str:
    """Render .env content using config templates.

    Substitution variables available in templates:
      - {worktree_path}: Full path to the worktree
      - {repo_root}: Path to the repository root
      - {name}: Name of the worktree

    Args:
        cfg: Loaded configuration containing env templates
        worktree_path: Path to the worktree
        repo_root: Repository root path
        name: Worktree name

    Returns:
        Formatted .env file content as string
    """
    variables: Mapping[str, str] = {
        "worktree_path": str(worktree_path),
        "repo_root": str(repo_root),
        "name": name,
    }

    lines: list[str] = []
    for key, template in cfg.env.items():
        value = template.format(**variables)
        # Quote value to be safe; dotenv parsers commonly accept quotes.
        lines.append(f"{key}={quote_env_value(value)}")

    # Always include these basics for convenience
    lines.append(f"WORKTREE_PATH={quote_env_value(str(worktree_path))}")
    lines.append(f"REPO_ROOT={quote_env_value(str(repo_root))}")
    lines.append(f"WORKTREE_NAME={quote_env_value(name)}")

    return "\n".join(lines) + "\n"


def quote_env_value(value: str) -> str:
    """Quote value for .env files.

    Escapes backslashes and quotes, then wraps in double quotes.

    Args:
        value: Value to quote

    Returns:
        Quoted value safe for .env files
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def run_post_create_commands(
    commands: Iterable[str],
    worktree_path: Path,
    shell: str | None,
) -> None:
    """Run post-create commands in worktree directory.

    Each command is executed in its own subprocess. Commands run serially.

    Args:
        commands: Commands to execute
        worktree_path: Working directory for command execution
        shell: Shell to use (e.g., "bash"), or None to tokenize with shlex

    Raises:
        SystemExit: If any command fails (via run_with_error_reporting)
    """
    for cmd in commands:
        cmd_list = [shell, "-lc", cmd] if shell else shlex.split(cmd)
        run_with_error_reporting(
            cmd_list,
            cwd=worktree_path,
            error_prefix="Post-create command failed",
            troubleshooting=[
                "The worktree was created successfully, but a post-create command failed",
                "You can still use the worktree or re-run the command manually",
            ],
        )
