"""Global configuration data structures and loading.

Provides immutable global config data loaded from ~/.workstack/config.toml.
Replaces lazy-loading GlobalConfigOps pattern with eager loading at entry point.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GlobalConfig:
    """Immutable global configuration data.

    Loaded once at CLI entry point and stored in WorkstackContext.
    All fields are read-only after construction.
    """

    workstacks_root: Path
    use_graphite: bool
    shell_setup_complete: bool
    show_pr_info: bool
    show_pr_checks: bool


def load_global_config(path: Path | None = None) -> GlobalConfig:
    """Load global config from ~/.workstack/config.toml.

    Args:
        path: Config file path (defaults to ~/.workstack/config.toml)

    Returns:
        GlobalConfig instance with loaded values

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is missing required fields or malformed
    """
    config_path = path if path is not None else Path.home() / ".workstack" / "config.toml"

    if not config_path.exists():
        raise FileNotFoundError(f"Global config not found at {config_path}")

    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    root = data.get("workstacks_root")
    if not root:
        raise ValueError(f"Missing 'workstacks_root' in {config_path}")

    return GlobalConfig(
        workstacks_root=Path(root).expanduser().resolve(),
        use_graphite=bool(data.get("use_graphite", False)),
        shell_setup_complete=bool(data.get("shell_setup_complete", False)),
        show_pr_info=bool(data.get("show_pr_info", True)),
        show_pr_checks=bool(data.get("show_pr_checks", False)),
    )


def save_global_config(config: GlobalConfig, path: Path | None = None) -> None:
    """Save global config to ~/.workstack/config.toml.

    Args:
        config: GlobalConfig instance to save
        path: Config file path (defaults to ~/.workstack/config.toml)
    """
    config_path = path if path is not None else Path.home() / ".workstack" / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    content = f"""# Global workstack configuration
workstacks_root = "{config.workstacks_root}"
use_graphite = {str(config.use_graphite).lower()}
shell_setup_complete = {str(config.shell_setup_complete).lower()}
show_pr_info = {str(config.show_pr_info).lower()}
show_pr_checks = {str(config.show_pr_checks).lower()}
"""
    config_path.write_text(content, encoding="utf-8")


def global_config_exists(path: Path | None = None) -> bool:
    """Check if global config file exists.

    Args:
        path: Config file path (defaults to ~/.workstack/config.toml)

    Returns:
        True if config exists, False otherwise
    """
    config_path = path if path is not None else Path.home() / ".workstack" / "config.toml"
    return config_path.exists()


def global_config_path() -> Path:
    """Get the path to the global config file.

    Returns:
        Path to config file (for error messages and debugging)
    """
    return Path.home() / ".workstack" / "config.toml"
