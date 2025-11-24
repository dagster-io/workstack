"""Fake implementation of ClaudeExecutor for testing.

This fake enables testing Claude command execution without
requiring the actual Claude CLI or using subprocess mocks.
"""

from pathlib import Path

from erk.core.claude_executor import ClaudeExecutor


class FakeClaudeExecutor(ClaudeExecutor):
    """In-memory fake implementation of Claude CLI execution.

    Constructor Injection:
    - All state is provided via constructor parameters
    - Mutations are tracked in read-only properties

    When to Use:
    - Testing commands that execute Claude CLI (e.g., erk implement --no-interactive)
    - Simulating Claude CLI availability
    - Verifying command execution without actual subprocess calls

    Examples:
        # Test with Claude available and successful execution
        >>> executor = FakeClaudeExecutor(claude_available=True)
        >>> executor.execute_command("/erk:implement-plan", Path("/repo"), False)
        >>> assert len(executor.executed_commands) == 1

        # Test with Claude not available
        >>> executor = FakeClaudeExecutor(claude_available=False)
        >>> assert not executor.is_claude_available()

        # Test command failure
        >>> executor = FakeClaudeExecutor(command_should_fail=True)
        >>> try:
        ...     executor.execute_command("/bad-command", Path("/repo"), False)
        ... except RuntimeError:
        ...     print("Command failed as expected")
    """

    def __init__(
        self,
        *,
        claude_available: bool = True,
        command_should_fail: bool = False,
    ) -> None:
        """Initialize fake with predetermined behavior.

        Args:
            claude_available: Whether Claude CLI should appear available
            command_should_fail: Whether execute_command should raise RuntimeError
        """
        self._claude_available = claude_available
        self._command_should_fail = command_should_fail
        self._executed_commands: list[tuple[str, Path, bool]] = []

    def is_claude_available(self) -> bool:
        """Return the availability configured at construction time."""
        return self._claude_available

    def execute_command(
        self, command: str, worktree_path: Path, dangerous: bool
    ) -> None:
        """Track command execution without running subprocess.

        This method records the call parameters for test assertions.
        It does not execute any actual subprocess operations.

        Raises:
            RuntimeError: If command_should_fail was set to True
        """
        self._executed_commands.append((command, worktree_path, dangerous))

        if self._command_should_fail:
            raise RuntimeError(f"Claude command {command} failed (simulated failure)")

    @property
    def executed_commands(self) -> list[tuple[str, Path, bool]]:
        """Get the list of execute_command() calls that were made.

        Returns list of (command, worktree_path, dangerous) tuples.

        This property is for test assertions only.
        """
        return self._executed_commands.copy()
