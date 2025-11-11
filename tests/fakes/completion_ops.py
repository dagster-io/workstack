"""Fake implementation of CompletionOps for testing.

This fake enables testing completion-related functionality without
requiring subprocess execution or actual Click completion generation.
"""

from workstack.core.completion_ops import CompletionOps


class FakeCompletionOps(CompletionOps):
    """In-memory fake implementation of completion operations.

    Constructor Injection:
    - All state is provided via constructor parameters
    - Tracks generation calls for test assertions

    Mutation Tracking:
    - generation_calls: List of shells for which completion was generated

    When to Use:
    - Testing completion commands (bash, zsh, fish)
    - Verifying correct shell-specific script generation
    - Testing workstack path detection logic

    Examples:
        # Test basic bash completion generation
        >>> completion_ops = FakeCompletionOps(
        ...     bash_script="# bash completion"
        ... )
        >>> script = completion_ops.generate_bash()
        >>> assert script == "# bash completion"
        >>> assert "bash" in completion_ops.generation_calls

        # Test multiple shell completions
        >>> completion_ops = FakeCompletionOps(
        ...     bash_script="# bash",
        ...     zsh_script="# zsh",
        ...     fish_script="# fish"
        ... )
        >>> bash = completion_ops.generate_bash()
        >>> zsh = completion_ops.generate_zsh()
        >>> assert completion_ops.generation_calls == ["bash", "zsh"]

        # Test custom workstack path
        >>> completion_ops = FakeCompletionOps(
        ...     workstack_path="/custom/path/workstack"
        ... )
        >>> path = completion_ops.get_workstack_path()
        >>> assert path == "/custom/path/workstack"
    """

    def __init__(
        self,
        *,
        bash_script: str = "# bash completion script",
        zsh_script: str = "# zsh completion script",
        fish_script: str = "# fish completion script",
        workstack_path: str = "/usr/local/bin/workstack",
    ) -> None:
        """Initialize fake with predetermined completion scripts.

        Args:
            bash_script: Script to return from generate_bash()
            zsh_script: Script to return from generate_zsh()
            fish_script: Script to return from generate_fish()
            workstack_path: Path to return from get_workstack_path()
        """
        self._bash_script = bash_script
        self._zsh_script = zsh_script
        self._fish_script = fish_script
        self._workstack_path = workstack_path
        self._generation_calls: list[str] = []

    def generate_bash(self) -> str:
        """Return pre-configured bash completion script and track the call."""
        self._generation_calls.append("bash")
        return self._bash_script

    def generate_zsh(self) -> str:
        """Return pre-configured zsh completion script and track the call."""
        self._generation_calls.append("zsh")
        return self._zsh_script

    def generate_fish(self) -> str:
        """Return pre-configured fish completion script and track the call."""
        self._generation_calls.append("fish")
        return self._fish_script

    def get_workstack_path(self) -> str:
        """Return pre-configured workstack executable path."""
        return self._workstack_path

    @property
    def generation_calls(self) -> list[str]:
        """Get list of shell types for which completion was generated.

        Returns copy to prevent external mutation.
        This property is for test assertions only.

        Example:
            >>> completion_ops = FakeCompletionOps()
            >>> completion_ops.generate_bash()
            >>> completion_ops.generate_zsh()
            >>> assert completion_ops.generation_calls == ["bash", "zsh"]
        """
        return self._generation_calls.copy()
