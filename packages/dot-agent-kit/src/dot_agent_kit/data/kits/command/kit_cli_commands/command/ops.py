"""Ops interface for Claude CLI execution."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandExecutionResult:
    """Result of command execution."""

    returncode: int


class ClaudeCliOps(ABC):
    """Abstract interface for executing Claude CLI commands."""

    @abstractmethod
    def execute_command(
        self,
        command_name: str,
        cwd: Path,
        json_output: bool,
    ) -> CommandExecutionResult:
        """Execute a Claude Code slash command.

        Args:
            command_name: Name of the command (e.g., "ensure-ci" or "gt:submit-branch")
            cwd: Working directory for execution
            json_output: Whether to use JSON output format

        Returns:
            CommandExecutionResult with exit code

        Raises:
            FileNotFoundError: If claude CLI binary not found
        """
        pass


class RealClaudeCliOps(ClaudeCliOps):
    """Real implementation using subprocess to invoke Claude CLI."""

    def execute_command(
        self,
        command_name: str,
        cwd: Path,
        json_output: bool,
    ) -> CommandExecutionResult:
        """Execute Claude CLI via subprocess with streaming output."""
        import json
        import subprocess

        # Print status message before launching
        print(f"Executing command: /{command_name}...", flush=True)

        # Build claude CLI command - always use stream-json for real-time output
        cmd = [
            "claude",
            "--print",
            "--verbose",  # Required for stream-json with --print
            "--permission-mode",
            "bypassPermissions",
            "--setting-sources",
            "project",
            "--output-format",
            "stream-json",  # Always use streaming JSON for real-time output
        ]

        # Invoke slash command
        cmd.append(f"/{command_name}")

        # Execute Claude Code CLI with streaming output
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            text=True,
            bufsize=1,  # Line buffered
        )

        # Stream output line by line, parsing JSONL format
        if process.stdout is not None:
            for line in process.stdout:
                # Parse JSONL and extract text content from assistant messages
                try:
                    msg = json.loads(line)
                    # Extract text from assistant messages
                    if msg.get("role") == "assistant":
                        content = msg.get("content", [])
                        for item in content:
                            if item.get("type") == "text":
                                text = item.get("text", "")
                                print(text, end="", flush=True)
                except json.JSONDecodeError:
                    # If JSON parsing fails, print raw line
                    print(line, end="", flush=True)

        # Wait for process to complete
        returncode = process.wait()

        return CommandExecutionResult(returncode=returncode)


class FakeClaudeCliOps(ClaudeCliOps):
    """Fake implementation for testing."""

    def __init__(self) -> None:
        """Initialize fake with tracking."""
        self._executions: list[tuple[str, Path, bool]] = []
        self._next_returncode: int = 0
        self._should_raise_file_not_found: bool = False

    def execute_command(
        self,
        command_name: str,
        cwd: Path,
        json_output: bool,
    ) -> CommandExecutionResult:
        """Record execution and return configured result."""
        self._executions.append((command_name, cwd, json_output))

        if self._should_raise_file_not_found:
            raise FileNotFoundError("claude CLI not found")

        return CommandExecutionResult(returncode=self._next_returncode)

    # Mutation tracking (read-only access for tests)

    @property
    def executions(self) -> list[tuple[str, Path, bool]]:
        """Return list of (command_name, cwd, json_output) tuples."""
        return list(self._executions)

    def get_execution_count(self) -> int:
        """Return number of executions."""
        return len(self._executions)

    def get_last_execution(self) -> tuple[str, Path, bool] | None:
        """Return last execution or None."""
        if not self._executions:
            return None
        return self._executions[-1]

    # Configuration methods for tests

    def set_next_returncode(self, returncode: int) -> None:
        """Configure the return code for next execution."""
        self._next_returncode = returncode

    def set_file_not_found_error(self, should_raise: bool) -> None:
        """Configure whether to raise FileNotFoundError."""
        self._should_raise_file_not_found = should_raise
