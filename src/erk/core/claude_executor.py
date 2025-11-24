"""Claude CLI execution abstraction.

This module provides abstraction over Claude CLI execution, enabling
dependency injection for testing without mock.patch.
"""

import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path


class ClaudeExecutor(ABC):
    """Abstract interface for Claude CLI execution.

    This abstraction enables testing without mock.patch by making Claude
    execution an injectable dependency.
    """

    @abstractmethod
    def is_claude_available(self) -> bool:
        """Check if Claude CLI is installed and available in PATH.

        Returns:
            True if Claude CLI is available, False otherwise.

        Example:
            >>> executor = RealClaudeExecutor()
            >>> if executor.is_claude_available():
            ...     print("Claude CLI is installed")
        """
        ...

    @abstractmethod
    def execute_command(self, command: str, worktree_path: Path, dangerous: bool) -> None:
        """Execute a Claude CLI slash command in non-interactive mode.

        Args:
            command: The slash command to execute (e.g., "/erk:implement-plan")
            worktree_path: Path to worktree directory to run command in
            dangerous: Whether to skip permission prompts

        Raises:
            RuntimeError: If Claude CLI command fails (non-zero exit code)

        Example:
            >>> executor = RealClaudeExecutor()
            >>> executor.execute_command(
            ...     "/erk:implement-plan",
            ...     Path("/repos/my-project"),
            ...     dangerous=False
            ... )
        """
        ...


class RealClaudeExecutor(ClaudeExecutor):
    """Production implementation using subprocess and Claude CLI."""

    def is_claude_available(self) -> bool:
        """Check if Claude CLI is in PATH using shutil.which."""
        return shutil.which("claude") is not None

    def execute_command(self, command: str, worktree_path: Path, dangerous: bool) -> None:
        """Execute Claude CLI command via subprocess.

        Implementation details:
        - Uses subprocess.run() with stdin=DEVNULL for non-interactive execution
        - Passes --permission-mode acceptEdits and optional --dangerously-skip-permissions
        - Streams output to terminal (no capture)
        - Raises RuntimeError on non-zero exit code
        """
        cmd_args = ["claude", "--permission-mode", "acceptEdits"]
        if dangerous:
            cmd_args.append("--dangerously-skip-permissions")
        cmd_args.append(command)

        result = subprocess.run(
            cmd_args,
            cwd=worktree_path,
            stdin=subprocess.DEVNULL,  # Prevent interaction
            # Don't capture stdout/stderr - let output stream to terminal
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Claude command {command} failed with exit code {result.returncode}"
            )
