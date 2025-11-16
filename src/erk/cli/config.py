import tomllib
from dataclasses import dataclass
from pathlib import Path


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
