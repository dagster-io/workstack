"""Claude CLI execution abstraction.

This module provides abstraction over Claude CLI execution, enabling
dependency injection for testing without mock.patch.
"""

import json
import os
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


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
    def execute_command(
        self, command: str, worktree_path: Path, dangerous: bool, verbose: bool = False
    ) -> CommandResult:
        """Execute a Claude CLI slash command in non-interactive mode.

        Args:
            command: The slash command to execute (e.g., "/erk:implement-plan")
            worktree_path: Path to worktree directory to run command in
            dangerous: Whether to skip permission prompts
            verbose: Whether to show raw output (True) or filtered output (False)

        Returns:
            CommandResult containing success status, PR URL, duration, and messages

        Raises:
            RuntimeError: If Claude CLI command fails (non-zero exit code)

        Example:
            >>> executor = RealClaudeExecutor()
            >>> result = executor.execute_command(
            ...     "/erk:implement-plan",
            ...     Path("/repos/my-project"),
            ...     dangerous=False,
            ...     verbose=False
            ... )
            >>> if result.success:
            ...     print(f"PR created: {result.pr_url}")
        """
        ...

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

    def execute_command(
        self, command: str, worktree_path: Path, dangerous: bool, verbose: bool = False
    ) -> CommandResult:
        """Execute Claude CLI command via subprocess.

        Implementation details:
        - Uses subprocess.run() with stdin=DEVNULL for non-interactive execution
        - Passes --permission-mode acceptEdits, --output-format stream-json
        - Optionally passes --dangerously-skip-permissions when dangerous=True
        - In verbose mode: streams output to terminal (no capture)
        - In filtered mode: captures and parses stream-json output
        - Returns CommandResult with success status, PR URL, duration, and messages
        """
        start_time = time.time()

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
            # Verbose mode - stream to terminal, no parsing
            result = subprocess.run(cmd_args, cwd=worktree_path, check=False)
            duration = time.time() - start_time

            if result.returncode != 0:
                error_msg = f"Claude command {command} failed with exit code {result.returncode}"
                return CommandResult(
                    success=False,
                    pr_url=None,
                    duration_seconds=duration,
                    error_message=error_msg,
                    filtered_messages=[],
                )

            return CommandResult(
                success=True,
                pr_url=None,
                duration_seconds=duration,
                error_message=None,
                filtered_messages=[],
            )

        # Filtered mode - capture output and parse stream-json
        result = subprocess.run(
            cmd_args,
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False,
        )
        duration = time.time() - start_time

        # Parse stream-json output
        filtered_messages: list[str] = []
        pr_url: str | None = None

        if result.stdout:
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue

                # Try to parse as JSON
                parsed = self._parse_stream_json_line(line, worktree_path)
                if parsed is None:
                    continue

                # Extract text content
                text_content = parsed.get("text_content")
                if text_content is not None:
                    filtered_messages.append(text_content)

                # Extract tool summaries
                tool_summary = parsed.get("tool_summary")
                if tool_summary is not None:
                    filtered_messages.append(tool_summary)

                # Extract PR URL
                if parsed.get("pr_url"):
                    pr_url = parsed["pr_url"]

        if result.returncode != 0:
            error_msg = f"Claude command {command} failed with exit code {result.returncode}"
            if result.stderr:
                error_msg += f"\n{result.stderr}"

            return CommandResult(
                success=False,
                pr_url=pr_url,
                duration_seconds=duration,
                error_message=error_msg,
                filtered_messages=filtered_messages,
            )

        return CommandResult(
            success=True,
            pr_url=pr_url,
            duration_seconds=duration,
            error_message=None,
            filtered_messages=filtered_messages,
        )

    def _parse_stream_json_line(
        self, line: str, worktree_path: Path
    ) -> dict[str, str | None] | None:
        """Parse a single stream-json line and extract relevant information.

        Args:
            line: JSON line from stream-json output
            worktree_path: Path to worktree for relativizing paths

        Returns:
            Dict with text_content, tool_summary, and pr_url keys, or None if not JSON
        """
        # Import here to avoid circular dependency
        from erk.core.output_filter import (
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
            "pr_url": None,
        }

        # Extract text from assistant messages
        if data.get("type") == "assistant_message":
            text = extract_text_content(data)
            if text:
                result["text_content"] = text

            # Extract tool summaries
            content = data.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        summary = summarize_tool_use(item, worktree_path)
                        if summary:
                            result["tool_summary"] = summary
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
