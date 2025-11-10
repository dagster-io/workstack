"""Fake global config operations for testing.

FakeGlobalConfigOps is an in-memory implementation that accepts pre-configured state
in its constructor. All state is held in memory - no filesystem access.
"""

from pathlib import Path

from workstack.core.global_config_ops import _UNCHANGED, GlobalConfigOps, _UnchangedType


class FakeGlobalConfigOps(GlobalConfigOps):
    """In-memory fake implementation - no filesystem access.

    All state is held in memory. Constructor accepts optional initial field values.
    This class has NO filesystem operations - all state is in-memory only.
    """

    def __init__(
        self,
        *,
        workstacks_root: Path | None = None,
        use_graphite: bool = False,
        shell_setup_complete: bool = False,
        show_pr_info: bool = True,
        show_pr_checks: bool = False,
        exists: bool = True,
        config_path: Path | None = None,
    ) -> None:
        """Create fake with optional pre-configured state.

        Args:
            workstacks_root: Initial workstacks root. If None and exists=True, raises
                           FileNotFoundError on getter calls (invalid state).
            use_graphite: Initial graphite preference (default: False)
            shell_setup_complete: Initial shell setup status (default: False)
            show_pr_info: Initial PR info display preference (default: True)
            show_pr_checks: Initial CI check display preference (default: False)
            exists: Whether config "exists". If False, getters raise FileNotFoundError.
            config_path: Path to report in error messages and get_path().
                        Defaults to /fake/config.toml for testing.

        Example:
            # Config that exists with specific values
            >>> fake = FakeGlobalConfigOps(
            ...     workstacks_root=Path("/tmp/workstacks"),
            ...     use_graphite=True,
            ...     shell_setup_complete=False,
            ... )
            >>> fake.get_workstacks_root()  # Returns Path("/tmp/workstacks")

            # Config that doesn't exist
            >>> fake = FakeGlobalConfigOps(exists=False)
            >>> fake.get_workstacks_root()  # Raises FileNotFoundError
        """
        self._workstacks_root = workstacks_root
        self._use_graphite = use_graphite
        self._shell_setup_complete = shell_setup_complete
        self._show_pr_info = show_pr_info
        self._show_pr_checks = show_pr_checks
        self._exists = exists
        self._path = config_path if config_path is not None else Path("/fake/config.toml")

    def get_workstacks_root(self) -> Path:
        if not self._exists:
            raise FileNotFoundError(f"Global config not found at {self._path}")
        if self._workstacks_root is None:
            raise ValueError(f"Missing 'workstacks_root' in {self._path}")
        return self._workstacks_root

    def get_use_graphite(self) -> bool:
        if not self._exists:
            raise FileNotFoundError(f"Global config not found at {self._path}")
        return self._use_graphite

    def get_shell_setup_complete(self) -> bool:
        if not self._exists:
            raise FileNotFoundError(f"Global config not found at {self._path}")
        return self._shell_setup_complete

    def get_show_pr_info(self) -> bool:
        if not self._exists:
            raise FileNotFoundError(f"Global config not found at {self._path}")
        return self._show_pr_info

    def get_show_pr_checks(self) -> bool:
        if not self._exists:
            raise FileNotFoundError(f"Global config not found at {self._path}")
        return self._show_pr_checks

    def set(
        self,
        *,
        workstacks_root: Path | _UnchangedType = _UNCHANGED,
        use_graphite: bool | _UnchangedType = _UNCHANGED,
        shell_setup_complete: bool | _UnchangedType = _UNCHANGED,
        show_pr_info: bool | _UnchangedType = _UNCHANGED,
        show_pr_checks: bool | _UnchangedType = _UNCHANGED,
    ) -> None:
        """Update config fields in memory (not filesystem).

        Creates config if it doesn't exist (sets _exists=True).
        """
        # Check if at least one field is being updated
        if (
            isinstance(workstacks_root, _UnchangedType)
            and isinstance(use_graphite, _UnchangedType)
            and isinstance(shell_setup_complete, _UnchangedType)
            and isinstance(show_pr_info, _UnchangedType)
            and isinstance(show_pr_checks, _UnchangedType)
        ):
            raise ValueError("At least one field must be provided")

        # Handle new config creation
        if not self._exists:
            if isinstance(workstacks_root, _UnchangedType):
                raise ValueError("workstacks_root must be provided for new config")
            self._workstacks_root = workstacks_root
            self._use_graphite = False if isinstance(use_graphite, _UnchangedType) else use_graphite
            self._shell_setup_complete = (
                False if isinstance(shell_setup_complete, _UnchangedType) else shell_setup_complete
            )
            self._show_pr_info = True if isinstance(show_pr_info, _UnchangedType) else show_pr_info
            self._show_pr_checks = (
                False if isinstance(show_pr_checks, _UnchangedType) else show_pr_checks
            )
            self._exists = True
            return

        # Update existing config
        if not isinstance(workstacks_root, _UnchangedType):
            self._workstacks_root = workstacks_root

        if not isinstance(use_graphite, _UnchangedType):
            self._use_graphite = use_graphite

        if not isinstance(shell_setup_complete, _UnchangedType):
            self._shell_setup_complete = shell_setup_complete

        if not isinstance(show_pr_info, _UnchangedType):
            self._show_pr_info = show_pr_info

        if not isinstance(show_pr_checks, _UnchangedType):
            self._show_pr_checks = show_pr_checks

    def exists(self) -> bool:
        return self._exists

    def get_path(self) -> Path:
        return self._path
