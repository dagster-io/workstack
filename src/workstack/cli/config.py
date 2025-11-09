import tomllib
from dataclasses import dataclass
from pathlib import Path

import tomlkit

from workstack.cli.config_schema import RepoConfig


@dataclass(frozen=True)
class LoadedConfig:
    """In-memory representation of `.workstack/config.toml`."""

    env: dict[str, str]
    post_create_commands: list[str]
    post_create_shell: str | None


def load_config(config_dir: Path) -> LoadedConfig:
    """Load config.toml from the given directory if present; otherwise return defaults.

    Example config:
      [env]
      DAGSTER_GIT_REPO_DIR = "{worktree_path}"

      [post_create]
      shell = "bash"
      commands = [
        "uv venv",
        "uv run make dev_install",
      ]
    """

    cfg_path = config_dir / "config.toml"
    if not cfg_path.exists():
        return LoadedConfig(env={}, post_create_commands=[], post_create_shell=None)

    data = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
    env = {str(k): str(v) for k, v in data.get("env", {}).items()}
    post = data.get("post_create", {})
    commands = [str(x) for x in post.get("commands", [])]
    shell = post.get("shell")
    if shell is not None:
        shell = str(shell)
    return LoadedConfig(env=env, post_create_commands=commands, post_create_shell=shell)


def save_config(config_dir: Path, config: LoadedConfig) -> None:
    """Save LoadedConfig to config.toml, preserving formatting.

    Creates the config directory if it doesn't exist.
    Uses tomlkit to preserve TOML formatting and comments.
    """
    config_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = config_dir / "config.toml"

    # Build TOML document
    doc = tomlkit.document()

    # Add env section if not empty
    if config.env:
        doc["env"] = config.env

    # Add post_create section if any settings
    if config.post_create_commands or config.post_create_shell:
        post_create = tomlkit.table()
        if config.post_create_shell:
            post_create["shell"] = config.post_create_shell
        if config.post_create_commands:
            post_create["commands"] = config.post_create_commands
        doc["post_create"] = post_create

    # Write to disk
    cfg_path.write_text(tomlkit.dumps(doc), encoding="utf-8")


def load_repo_config(repo_root: Path, workstacks_dir: Path) -> RepoConfig:
    """Load repo config from all sources.

    Combines:
    - trunk_branch from pyproject.toml [tool.workstack]
    - env, post_create_* from .workstack/config.toml

    Related Context:
    - Loading stays in cli/config.py (user preference for module organization)
    - Uses existing load_config() for .workstack/config.toml (reuse LoadedConfig)
    """
    from workstack.core.context import read_trunk_from_pyproject

    trunk_branch = read_trunk_from_pyproject(repo_root)
    loaded = load_config(workstacks_dir)

    return RepoConfig(
        trunk_branch=trunk_branch,
        env=loaded.env,
        post_create_commands=loaded.post_create_commands,
        post_create_shell=loaded.post_create_shell,
    )
