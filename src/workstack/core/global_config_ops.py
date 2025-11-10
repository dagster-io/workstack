"""Global configuration operations interface and implementations."""

import tomllib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Final

import click


class _UnchangedType:
    """Sentinel type for unchanged config values."""

    pass


_UNCHANGED: Final = _UnchangedType()


class GlobalConfigOps(ABC):
    """Abstract interface for global configuration operations.

    All implementations (real and fake) must implement this interface.
    This interface provides direct access to config fields via getters and a single
    setter method using sentinel pattern for optional updates.
    """

    @abstractmethod
    def get_workstacks_root(self) -> Path:
        """Get workstacks root directory.

        Returns:
            Path to workstacks root directory

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        ...

    @abstractmethod
    def get_use_graphite(self) -> bool:
        """Get graphite usage preference.

        Returns:
            True if graphite should be used, False otherwise

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        ...

    @abstractmethod
    def get_shell_setup_complete(self) -> bool:
        """Get shell setup completion status.

        Returns:
            True if shell setup is complete, False otherwise

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        ...

    @abstractmethod
    def get_show_pr_info(self) -> bool:
        """Get whether to show PR information in ls output.

        Returns:
            True if PR info should be shown, False otherwise

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        ...

    @abstractmethod
    def get_show_pr_checks(self) -> bool:
        """Get whether to show CI check status in PR info.

        When True, fetches CI status from GitHub API (slower).
        When False, only shows basic PR info from Graphite cache (faster).

        Returns:
            True if CI check status should be shown, False otherwise

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        ...

    @abstractmethod
    def set(
        self,
        *,
        workstacks_root: Path | _UnchangedType = _UNCHANGED,
        use_graphite: bool | _UnchangedType = _UNCHANGED,
        shell_setup_complete: bool | _UnchangedType = _UNCHANGED,
        show_pr_info: bool | _UnchangedType = _UNCHANGED,
        show_pr_checks: bool | _UnchangedType = _UNCHANGED,
    ) -> None:
        """Update config fields. Only provided fields are changed.

        Creates config file if it doesn't exist. Only fields that are not _UNCHANGED
        will be updated. At least one field must be provided.

        Args:
            workstacks_root: New workstacks root, or _UNCHANGED to keep current
            use_graphite: New graphite preference, or _UNCHANGED to keep current
            shell_setup_complete: New shell setup status, or _UNCHANGED to keep current
            show_pr_info: New PR info display preference, or _UNCHANGED to keep current
            show_pr_checks: New CI check display preference, or _UNCHANGED to keep current

        Raises:
            ValueError: If all fields are _UNCHANGED (nothing to update)
        """
        ...

    @abstractmethod
    def exists(self) -> bool:
        """Check if global config file exists.

        Returns:
            True if config exists, False otherwise
        """
        ...

    @abstractmethod
    def get_path(self) -> Path:
        """Get the path to the global config file.

        Returns:
            Path to config file (for error messages and debugging)
        """
        ...


# ============================================================================
# Production Implementation
# ============================================================================


class RealGlobalConfigOps(GlobalConfigOps):
    """Production implementation using ~/.workstack/config.toml with lazy loading."""

    def __init__(self) -> None:
        self._path = Path.home() / ".workstack" / "config.toml"
        self._cache: dict[str, Path | bool] | None = None

    def _load_cache(self) -> dict[str, Path | bool]:
        """Load config from disk and cache it."""
        if not self._path.exists():
            raise FileNotFoundError(f"Global config not found at {self._path}")

        data = tomllib.loads(self._path.read_text(encoding="utf-8"))
        root = data.get("workstacks_root")
        if not root:
            raise ValueError(f"Missing 'workstacks_root' in {self._path}")

        return {
            "workstacks_root": Path(root).expanduser().resolve(),
            "use_graphite": bool(data.get("use_graphite", False)),
            "shell_setup_complete": bool(data.get("shell_setup_complete", False)),
            "show_pr_info": bool(data.get("show_pr_info", True)),
            "show_pr_checks": bool(data.get("show_pr_checks", False)),
        }

    def _ensure_cache(self) -> dict[str, Path | bool]:
        """Ensure cache is loaded and return it."""
        if self._cache is None:
            self._cache = self._load_cache()
        return self._cache

    def _invalidate_cache(self) -> None:
        """Invalidate cache after writes."""
        self._cache = None

    def get_workstacks_root(self) -> Path:
        cache = self._ensure_cache()
        result = cache["workstacks_root"]
        if not isinstance(result, Path):
            raise TypeError(f"Expected Path, got {type(result)}")
        return result

    def get_use_graphite(self) -> bool:
        cache = self._ensure_cache()
        result = cache["use_graphite"]
        if not isinstance(result, bool):
            raise TypeError(f"Expected bool, got {type(result)}")
        return result

    def get_shell_setup_complete(self) -> bool:
        cache = self._ensure_cache()
        result = cache["shell_setup_complete"]
        if not isinstance(result, bool):
            raise TypeError(f"Expected bool, got {type(result)}")
        return result

    def get_show_pr_info(self) -> bool:
        cache = self._ensure_cache()
        result = cache["show_pr_info"]
        if not isinstance(result, bool):
            raise TypeError(f"Expected bool, got {type(result)}")
        return result

    def get_show_pr_checks(self) -> bool:
        cache = self._ensure_cache()
        result = cache["show_pr_checks"]
        if not isinstance(result, bool):
            raise TypeError(f"Expected bool, got {type(result)}")
        return result

    def set(
        self,
        *,
        workstacks_root: Path | _UnchangedType = _UNCHANGED,
        use_graphite: bool | _UnchangedType = _UNCHANGED,
        shell_setup_complete: bool | _UnchangedType = _UNCHANGED,
        show_pr_info: bool | _UnchangedType = _UNCHANGED,
        show_pr_checks: bool | _UnchangedType = _UNCHANGED,
    ) -> None:
        # Check if at least one field is being updated
        if (
            isinstance(workstacks_root, _UnchangedType)
            and isinstance(use_graphite, _UnchangedType)
            and isinstance(shell_setup_complete, _UnchangedType)
            and isinstance(show_pr_info, _UnchangedType)
            and isinstance(show_pr_checks, _UnchangedType)
        ):
            raise ValueError("At least one field must be provided")

        # Get current values (if config exists), or use defaults
        if self.exists():
            current_root = self.get_workstacks_root()
            current_graphite = self.get_use_graphite()
            current_shell = self.get_shell_setup_complete()
            current_pr_info = self.get_show_pr_info()
            current_pr_checks = self.get_show_pr_checks()
        else:
            # For new config, all fields must be provided (no defaults)
            if isinstance(workstacks_root, _UnchangedType):
                raise ValueError("workstacks_root must be provided for new config")
            current_root = workstacks_root
            current_graphite = False
            current_shell = False
            current_pr_info = True
            current_pr_checks = False

        # Apply updates
        final_root = (
            current_root if isinstance(workstacks_root, _UnchangedType) else workstacks_root
        )
        final_graphite = (
            current_graphite if isinstance(use_graphite, _UnchangedType) else use_graphite
        )
        final_shell = (
            current_shell
            if isinstance(shell_setup_complete, _UnchangedType)
            else shell_setup_complete
        )
        final_pr_info = (
            current_pr_info if isinstance(show_pr_info, _UnchangedType) else show_pr_info
        )
        final_pr_checks = (
            current_pr_checks if isinstance(show_pr_checks, _UnchangedType) else show_pr_checks
        )

        # Write to disk
        self._path.parent.mkdir(parents=True, exist_ok=True)
        content = f"""# Global workstack configuration
workstacks_root = "{final_root}"
use_graphite = {str(final_graphite).lower()}
shell_setup_complete = {str(final_shell).lower()}
show_pr_info = {str(final_pr_info).lower()}
show_pr_checks = {str(final_pr_checks).lower()}
"""
        self._path.write_text(content, encoding="utf-8")
        self._invalidate_cache()

    def exists(self) -> bool:
        return self._path.exists()

    def get_path(self) -> Path:
        return self._path


# ============================================================================
# Dry-Run Wrapper
# ============================================================================


class DryRunGlobalConfigOps(GlobalConfigOps):
    """Dry-run wrapper for global config operations.

    Read operations are delegated to the wrapped implementation.
    Write operations print dry-run messages instead of modifying the config file.
    """

    def __init__(self, wrapped: GlobalConfigOps) -> None:
        """Initialize dry-run wrapper with a real implementation.

        Args:
            wrapped: The real global config operations implementation to wrap
        """
        self._wrapped = wrapped

    def get_workstacks_root(self) -> Path:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_workstacks_root()

    def get_use_graphite(self) -> bool:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_use_graphite()

    def get_shell_setup_complete(self) -> bool:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_shell_setup_complete()

    def get_show_pr_info(self) -> bool:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_show_pr_info()

    def get_show_pr_checks(self) -> bool:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_show_pr_checks()

    def set(
        self,
        *,
        workstacks_root: Path | _UnchangedType = _UNCHANGED,
        use_graphite: bool | _UnchangedType = _UNCHANGED,
        shell_setup_complete: bool | _UnchangedType = _UNCHANGED,
        show_pr_info: bool | _UnchangedType = _UNCHANGED,
        show_pr_checks: bool | _UnchangedType = _UNCHANGED,
    ) -> None:
        """Print dry-run message instead of updating config."""
        updates: list[str] = []
        if not isinstance(workstacks_root, _UnchangedType):
            updates.append(f"workstacks_root={workstacks_root}")
        if not isinstance(use_graphite, _UnchangedType):
            updates.append(f"use_graphite={use_graphite}")
        if not isinstance(shell_setup_complete, _UnchangedType):
            updates.append(f"shell_setup_complete={shell_setup_complete}")
        if not isinstance(show_pr_info, _UnchangedType):
            updates.append(f"show_pr_info={show_pr_info}")
        if not isinstance(show_pr_checks, _UnchangedType):
            updates.append(f"show_pr_checks={show_pr_checks}")

        if updates:
            click.echo(f"[DRY RUN] Would update config: {', '.join(updates)}", err=True)

    def exists(self) -> bool:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.exists()

    def get_path(self) -> Path:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_path()
