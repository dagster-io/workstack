"""Global configuration data structures and loading.

Provides immutable global config data loaded from ~/.erk/config.toml.
Replaces lazy-loading GlobalConfigOps pattern with eager loading at entry point.
"""

import tomllib
from abc import ABC, abstractmethod
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


class GlobalConfigOps(ABC):
    """Abstract interface for global config operations.

    Provides dependency injection for global config access, enabling
    in-memory implementations for tests without touching filesystem.
    """

    @abstractmethod
    def exists(self) -> bool:
        """Check if global config exists."""
        ...

    @abstractmethod
    def load(self) -> GlobalConfig:
        """Load global config.

        Returns:
            GlobalConfig instance with loaded values

        Raises:
            FileNotFoundError: If config doesn't exist
            ValueError: If config is missing required fields or malformed
        """
        ...

    @abstractmethod
    def save(self, config: GlobalConfig) -> None:
        """Save global config.

        Args:
            config: GlobalConfig instance to save
        """
        ...

    @abstractmethod
    def path(self) -> Path:
        """Get the path to the global config file.

        Returns:
            Path to config file (for error messages and debugging)
        """
        ...


class FilesystemGlobalConfigOps(GlobalConfigOps):
    """Production implementation that reads/writes ~/.erk/config.toml."""

    def exists(self) -> bool:
        """Check if global config file exists."""
        return self.path().exists()

    def load(self) -> GlobalConfig:
        """Load global config from ~/.erk/config.toml.

        Returns:
            GlobalConfig instance with loaded values

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is missing required fields or malformed
        """
        config_path = self.path()

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
        )

    def save(self, config: GlobalConfig) -> None:
        """Save global config to ~/.erk/config.toml.

        Args:
            config: GlobalConfig instance to save
        """
        config_path = self.path()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        content = f"""# Global erk configuration
workstacks_root = "{config.workstacks_root}"
use_graphite = {str(config.use_graphite).lower()}
shell_setup_complete = {str(config.shell_setup_complete).lower()}
show_pr_info = {str(config.show_pr_info).lower()}
"""
        config_path.write_text(content, encoding="utf-8")

    def path(self) -> Path:
        """Get the path to the global config file.

        Returns:
            Path to ~/.erk/config.toml
        """
        return Path.home() / ".erk" / "config.toml"


class InMemoryGlobalConfigOps(GlobalConfigOps):
    """Test implementation that stores config in memory without touching filesystem."""

    def __init__(self, config: GlobalConfig | None = None) -> None:
        """Initialize in-memory config ops.

        Args:
            config: Initial config state (None = config doesn't exist)
        """
        self._config = config

    def exists(self) -> bool:
        """Check if global config exists in memory."""
        return self._config is not None

    def load(self) -> GlobalConfig:
        """Load global config from memory.

        Returns:
            GlobalConfig instance stored in memory

        Raises:
            FileNotFoundError: If config doesn't exist in memory
        """
        if self._config is None:
            raise FileNotFoundError(f"Global config not found at {self.path()}")
        return self._config

    def save(self, config: GlobalConfig) -> None:
        """Save global config to memory.

        Args:
            config: GlobalConfig instance to store
        """
        self._config = config

    def path(self) -> Path:
        """Get fake path for error messages.

        Returns:
            Path to fake config location (for error messages)
        """
        return Path("/fake/erk/config.toml")
