"""Fake implementation of Shell for testing.

This fake enables testing shell-dependent functionality without
requiring specific shell configurations or installed tools.
"""

from pathlib import Path

from erk.core.shell import Shell


class FakeShell(Shell):
    """In-memory fake implementation of shell operations.

    Constructor Injection:
    - All state is provided via constructor parameters
    - No mutations occur (immutable after construction)

    When to Use:
    - Testing shell-dependent commands (e.g., init, shell setup)
    - Simulating different shell environments (bash, zsh, fish)
    - Testing behavior when tools are/aren't installed

    Examples:
        # Test with bash shell detected
        >>> shell_ops = FakeShell(
        ...     detected_shell=("bash", Path.home() / ".bashrc")
        ... )
        >>> result = shell_ops.detect_shell()
        >>> assert result == ("bash", Path.home() / ".bashrc")

        # Test with tool installed
        >>> shell_ops = FakeShell(
        ...     installed_tools={"gt": "/usr/local/bin/gt"}
        ... )
        >>> gt_path = shell_ops.get_installed_tool_path("gt")
        >>> assert gt_path == "/usr/local/bin/gt"

        # Test with no shell detected
        >>> shell_ops = FakeShell(detected_shell=None)
        >>> result = shell_ops.detect_shell()
        >>> assert result is None
    """

    def __init__(
        self,
        *,
        detected_shell: tuple[str, Path] | None = None,
        installed_tools: dict[str, str] | None = None,
        command_exit_code: int = 0,
    ) -> None:
        """Initialize fake with predetermined shell and tool availability.

        Args:
            detected_shell: Shell to return from detect_shell(), or None if no shell
                should be detected. Format: (shell_name, rc_file_path)
            installed_tools: Mapping of tool name to executable path. Tools not in
                this mapping will return None from get_installed_tool_path()
            command_exit_code: Exit code to return from run_command() (default: 0)
        """
        self._detected_shell = detected_shell
        self._installed_tools = installed_tools or {}
        self._command_exit_code = command_exit_code
        self._command_calls: list[tuple[list[str], Path | None]] = []
        self._sync_calls: list[tuple[Path, bool, bool]] = []

    def detect_shell(self) -> tuple[str, Path] | None:
        """Return the shell configured at construction time."""
        return self._detected_shell

    def get_installed_tool_path(self, tool_name: str) -> str | None:
        """Return the tool path if configured, None otherwise."""
        return self._installed_tools.get(tool_name)

    def run_command(self, command: list[str], cwd: Path | None = None) -> int:
        """Track call to run_command and return configured exit code.

        This method records the call parameters for test assertions.
        It does not execute any actual subprocess operations.

        Returns:
            Configured exit code (from command_exit_code parameter)
        """
        self._command_calls.append((command, cwd))
        return self._command_exit_code

    def run_erk_sync(self, repo_root: Path, *, force: bool, verbose: bool) -> None:
        """Track call to run_erk_sync without executing anything.

        This method records the call parameters for test assertions.
        It does not execute any actual subprocess operations.
        """
        self._sync_calls.append((repo_root, force, verbose))

    @property
    def command_calls(self) -> list[tuple[list[str], Path | None]]:
        """Get the list of run_command() calls that were made.

        Returns list of (command, cwd) tuples.

        This property is for test assertions only.
        """
        return self._command_calls.copy()

    @property
    def sync_calls(self) -> list[tuple[Path, bool, bool]]:
        """Get the list of run_erk_sync() calls that were made.

        Returns list of (repo_root, force, verbose) tuples.

        This property is for test assertions only.
        """
        return self._sync_calls.copy()
