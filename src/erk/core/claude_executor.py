"""Claude CLI execution abstraction.

This module provides abstraction over Claude CLI execution, enabling
dependency injection for testing without mock.patch.
"""

import json
import os
import shutil
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StreamEvent:
    """Event emitted during streaming execution.

    Attributes:
        event_type: Type of event ("text", "tool", "spinner_update", "pr_url")
        content: The content of the event (text message, tool summary, spinner text, or PR URL)
    """

    event_type: str
    content: str


@dataclass
class CommandResult:
    """Result of executing a Claude CLI command.

    Attributes:
        success: Whether the command completed successfully
        pr_url: Pull request URL if one was created, None otherwise
        duration_seconds: Execution time in seconds
        error_message: Error description if command failed, None otherwise
        filtered_messages: List of text messages and tool summaries for display
    """

    success: bool
    pr_url: str | None
    duration_seconds: float
    error_message: str | None
    filtered_messages: list[str] = field(default_factory=list)


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
    def execute_command_streaming(
        self,
        command: str,
        worktree_path: Path,
        dangerous: bool,
        verbose: bool = False,
    ) -> Iterator[StreamEvent]:
        """Execute Claude CLI command and yield StreamEvents in real-time.

        Args:
            command: The slash command to execute (e.g., "/erk:implement-plan")
            worktree_path: Path to worktree directory to run command in
            dangerous: Whether to skip permission prompts
            verbose: Whether to show raw output (True) or filtered output (False)

        Yields:
            StreamEvent objects as they occur during execution

        Example:
            >>> executor = RealClaudeExecutor()
            >>> for event in executor.execute_command_streaming(
            ...     "/erk:implement-plan",
            ...     Path("/repos/my-project"),
            ...     dangerous=False
            ... ):
            ...     if event.event_type == "tool":
            ...         print(f"Tool: {event.content}")
        """
        ...

    def execute_command(
        self,
        command: str,
        worktree_path: Path,
        dangerous: bool,
        verbose: bool = False,
    ) -> CommandResult:
        """Execute Claude CLI command and return final result (non-streaming).

        This is a convenience method that collects all streaming events
        and returns a final CommandResult. Use execute_command_streaming()
        for real-time updates.

        Args:
            command: The slash command to execute (e.g., "/erk:implement-plan")
            worktree_path: Path to worktree directory to run command in
            dangerous: Whether to skip permission prompts
            verbose: Whether to show raw output (True) or filtered output (False)

        Returns:
            CommandResult containing success status, PR URL, duration, and messages

        Example:
            >>> executor = RealClaudeExecutor()
            >>> result = executor.execute_command(
            ...     "/erk:implement-plan",
            ...     Path("/repos/my-project"),
            ...     dangerous=False
            ... )
            >>> if result.success:
            ...     print(f"PR created: {result.pr_url}")
        """
        start_time = time.time()
        filtered_messages: list[str] = []
        pr_url: str | None = None
        error_message: str | None = None
        success = True

        for event in self.execute_command_streaming(command, worktree_path, dangerous, verbose):
            if event.event_type == "text":
                filtered_messages.append(event.content)
            elif event.event_type == "tool":
                filtered_messages.append(event.content)
            elif event.event_type == "pr_url":
                pr_url = event.content
            elif event.event_type == "error":
                error_message = event.content
                success = False

        duration = time.time() - start_time
        return CommandResult(
            success=success,
            pr_url=pr_url,
            duration_seconds=duration,
            error_message=error_message,
            filtered_messages=filtered_messages,
        )

    @abstractmethod
    def execute_interactive(self, worktree_path: Path, dangerous: bool) -> None:
        """Execute Claude CLI in interactive mode by replacing current process.

        Args:
            worktree_path: Path to worktree directory to run in
            dangerous: Whether to skip permission prompts

        Raises:
            RuntimeError: If Claude CLI is not available

        Note:
            In production (RealClaudeExecutor), this function never returns - the
            process is replaced by Claude CLI via os.execvp. In testing
            (FakeClaudeExecutor), this simulates the behavior without actually
            replacing the process.

        Example:
            >>> executor = RealClaudeExecutor()
            >>> executor.execute_interactive(
            ...     Path("/repos/my-project"),
            ...     dangerous=False
            ... )
            # Never returns in production - process is replaced
        """
        ...


class RealClaudeExecutor(ClaudeExecutor):
    """Production implementation using subprocess and Claude CLI."""

    def is_claude_available(self) -> bool:
        """Check if Claude CLI is in PATH using shutil.which."""
        return shutil.which("claude") is not None

    def execute_command_streaming(
        self,
        command: str,
        worktree_path: Path,
        dangerous: bool,
        verbose: bool = False,
    ) -> Iterator[StreamEvent]:
        """Execute Claude CLI command and yield StreamEvents in real-time.

        Implementation details:
        - Uses subprocess.Popen() for streaming stdout line-by-line
        - Passes --permission-mode acceptEdits, --output-format stream-json
        - Optionally passes --dangerously-skip-permissions when dangerous=True
        - In verbose mode: streams output to terminal (no parsing, no events yielded)
        - In filtered mode: parses stream-json and yields events in real-time
        """
        cmd_args = [
            "claude",
            "--print",
            "--verbose",
            "--permission-mode",
            "acceptEdits",
            "--output-format",
            "stream-json",
        ]
        if dangerous:
            cmd_args.append("--dangerously-skip-permissions")
        cmd_args.append(command)

        if verbose:
            # Verbose mode - stream to terminal, no parsing, no events
            result = subprocess.run(cmd_args, cwd=worktree_path, check=False)

            if result.returncode != 0:
                error_msg = f"Claude command {command} failed with exit code {result.returncode}"
                yield StreamEvent("error", error_msg)
            return

        # Filtered mode - streaming with real-time parsing
        process = subprocess.Popen(
            cmd_args,
            cwd=worktree_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
        )

        stderr_output: list[str] = []

        # Capture stderr in background thread
        def capture_stderr() -> None:
            if process.stderr:
                for line in process.stderr:
                    stderr_output.append(line)

        stderr_thread = threading.Thread(target=capture_stderr, daemon=True)
        stderr_thread.start()

        # Process stdout line by line in real-time
        if process.stdout:
            for line in process.stdout:
                if not line.strip():
                    continue

                # Try to parse as JSON
                parsed = self._parse_stream_json_line(line, worktree_path, command)
                if parsed is None:
                    continue

                # Yield text content
                text_content = parsed.get("text_content")
                if text_content is not None:
                    yield StreamEvent("text", text_content)

                # Yield tool summaries
                tool_summary = parsed.get("tool_summary")
                if tool_summary is not None:
                    yield StreamEvent("tool", tool_summary)

                # Yield spinner updates
                spinner_text = parsed.get("spinner_update")
                if spinner_text is not None:
                    yield StreamEvent("spinner_update", spinner_text)

                # Yield PR URL
                pr_url_value = parsed.get("pr_url")
                if pr_url_value is not None:
                    yield StreamEvent("pr_url", pr_url_value)

        # Wait for process to complete
        returncode = process.wait()

        # Wait for stderr thread to finish
        stderr_thread.join(timeout=1.0)

        if returncode != 0:
            error_msg = f"Claude command {command} failed with exit code {returncode}"
            if stderr_output:
                error_msg += "\n" + "".join(stderr_output)
            yield StreamEvent("error", error_msg)

    def _parse_stream_json_line(
        self, line: str, worktree_path: Path, command: str
    ) -> dict[str, str | None] | None:
        """Parse a single stream-json line and extract relevant information.

        Args:
            line: JSON line from stream-json output
            worktree_path: Path to worktree for relativizing paths
            command: The slash command being executed

        Returns:
            Dict with text_content, tool_summary, spinner_update, and pr_url keys,
            or None if not JSON
        """
        # Import here to avoid circular dependency
        from erk.core.output_filter import (
            determine_spinner_status,
            extract_pr_url,
            extract_text_content,
            summarize_tool_use,
        )

        if not line.strip():
            return None

        # Parse JSON safely - JSON parsing requires exception handling
        data: dict | None = None
        if line.strip():
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    data = parsed
            except json.JSONDecodeError:
                return None

        if data is None:
            return None

        result: dict[str, str | None] = {
            "text_content": None,
            "tool_summary": None,
            "spinner_update": None,
            "pr_url": None,
        }

        # Extract text from assistant messages
        if data.get("type") == "assistant_message":
            text = extract_text_content(data)
            if text:
                result["text_content"] = text

            # Extract tool summaries and spinner updates
            content = data.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        summary = summarize_tool_use(item, worktree_path)
                        if summary:
                            result["tool_summary"] = summary

                        # Generate spinner update for all tools (even suppressible ones)
                        spinner_text = determine_spinner_status(item, command, worktree_path)
                        result["spinner_update"] = spinner_text
                        break

        # Extract PR URL from tool results
        if data.get("type") == "user_message":
            content = data.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_result":
                        tool_content = item.get("content")
                        if isinstance(tool_content, str):
                            pr_url = extract_pr_url(tool_content)
                            if pr_url:
                                result["pr_url"] = pr_url
                                break

        return result

    def execute_interactive(self, worktree_path: Path, dangerous: bool) -> None:
        """Execute Claude CLI in interactive mode by replacing current process.

        Implementation details:
        - Verifies Claude CLI is available
        - Changes to worktree directory
        - Builds command arguments with /erk:implement-plan
        - Replaces current process using os.execvp

        Note:
            This function never returns - the process is replaced by Claude CLI.
        """
        # Verify Claude is available
        if not self.is_claude_available():
            raise RuntimeError("Claude CLI not found\nInstall from: https://claude.com/download")

        # Change to worktree directory
        os.chdir(worktree_path)

        # Build command arguments
        cmd_args = ["claude", "--permission-mode", "acceptEdits"]
        if dangerous:
            cmd_args.append("--dangerously-skip-permissions")
        cmd_args.append("/erk:implement-plan")

        # Replace current process with Claude
        os.execvp("claude", cmd_args)
        # Never returns - process is replaced
