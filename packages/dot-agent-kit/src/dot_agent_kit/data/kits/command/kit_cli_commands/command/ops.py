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

        # Separator for visual clarity between message blocks
        separator = "─" * 60

        def print_separator() -> None:
            """Print visual separator line."""
            print(f"\n{separator}\n", flush=True)

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
                # Parse JSONL stream-json format
                # Message types: assistant, user, system, result
                try:
                    msg = json.loads(line)
                    msg_type = msg.get("type")

                    if msg_type == "assistant":
                        # Show text and tool use from assistant messages
                        message = msg.get("message", {})
                        content = message.get("content", [])
                        for item in content:
                            if item.get("type") == "text":
                                text = item.get("text", "")
                                print(text, end="", flush=True)
                            elif item.get("type") == "tool_use":
                                tool_name = item.get("name", "unknown")
                                tool_input = item.get("input", {})
                                # Show tool invocations
                                print(f"\n⚙️  Using {tool_name}", flush=True)
                                # Show all parameters for all tools
                                if tool_input:
                                    for param_name, param_value in tool_input.items():
                                        # Format parameter display
                                        if isinstance(param_value, str):
                                            # For string values, show inline or
                                            # indented for multiline
                                            if "\n" in param_value:
                                                print(f"   {param_name}:", flush=True)
                                                for line in param_value.split("\n"):
                                                    print(f"      {line}", flush=True)
                                            else:
                                                print(f"   {param_name}: {param_value}", flush=True)
                                        elif isinstance(param_value, (list, dict)):
                                            # For complex types, use JSON formatting
                                            json_str = json.dumps(
                                                param_value, indent=2, ensure_ascii=False
                                            )
                                            print(f"   {param_name}:", flush=True)
                                            for line in json_str.split("\n"):
                                                print(f"      {line}", flush=True)
                                        else:
                                            # For other types (int, bool, etc), show inline
                                            print(f"   {param_name}: {param_value}", flush=True)

                    elif msg_type == "system":
                        # Hide system messages (internal metadata)
                        pass

                    elif msg_type == "user":
                        # Display tool results from user messages
                        message = msg.get("message", {})
                        content = message.get("content", [])
                        for item in content:
                            if item.get("type") == "tool_result":
                                # Display result content
                                result_content = item.get("content")
                                if result_content:
                                    print("\n📤 Result:", flush=True)
                                    if isinstance(result_content, str):
                                        # Indent multiline results
                                        for line in result_content.split("\n"):
                                            print(f"   {line}", flush=True)
                                    elif isinstance(result_content, list):
                                        # Handle structured content
                                        for result_item in result_content:
                                            if isinstance(result_item, dict):
                                                if result_item.get("type") == "text":
                                                    text = result_item.get("text", "")
                                                    for line in text.split("\n"):
                                                        print(f"   {line}", flush=True)
                                is_error = item.get("is_error", False)
                                if is_error:
                                    print("   [Error result]", flush=True)

                    elif msg_type == "result":
                        # Show completion summary
                        is_error = msg.get("is_error", False)
                        status = "❌ Error" if is_error else "✅ Success"
                        cost = msg.get("total_cost_usd")
                        cost_str = f"${cost:.4f}" if cost else "N/A"
                        duration_ms = msg.get("duration_ms", 0)
                        print(
                            f"\n\n{status} - Cost: {cost_str}, Duration: {duration_ms}ms\n",
                            flush=True,
                        )

                except json.JSONDecodeError:
                    # If JSON parsing fails, print raw line
                    print(f"\n[Warning: Invalid JSON]: {line}", end="", flush=True)

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
