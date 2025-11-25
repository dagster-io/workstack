"""Shared helpers for programmatic Claude CLI execution.

This module provides reusable functions for executing Claude CLI commands
with streaming output, spinner updates, and consistent error handling.

Documentation: docs/agent/claude-cli-execution.md
    - Architecture diagram and layered design
    - Usage patterns with examples
    - Anti-patterns to avoid

IMPORTANT: Keep docs/agent/claude-cli-execution.md in sync with any changes to this module.
"""

import time
from pathlib import Path

import click
from rich.console import Console

from erk.core.claude_executor import ClaudeExecutor, CommandResult


def execute_streaming_command(
    executor: ClaudeExecutor,
    command: str,
    worktree_path: Path,
    dangerous: bool,
    verbose: bool,
) -> CommandResult:
    """Execute a single Claude CLI command with streaming output.

    Provides a Rich console spinner with real-time status updates in filtered mode,
    or simple pass-through output in verbose mode.

    Args:
        executor: ClaudeExecutor instance for command execution
        command: The slash command to execute (e.g., "/gt:submit-pr")
        worktree_path: Path to worktree directory to run command in
        dangerous: Whether to skip permission prompts
        verbose: Whether to show raw output (True) or filtered output (False)

    Returns:
        CommandResult containing success status, PR URL, duration, and messages

    Raises:
        click.ClickException: If Claude CLI not found or command fails
    """

    # Verify Claude is available
    if not executor.is_claude_available():
        raise click.ClickException(
            "Claude CLI not found\nInstall from: https://claude.com/download"
        )

    if verbose:
        # Verbose mode - simple output, no spinner
        click.echo(f"Running {command}...", err=True)
        result = executor.execute_command(command, worktree_path, dangerous, verbose=True)
    else:
        # Filtered mode - streaming with dynamic spinner updates
        console = Console()
        with console.status(f"Running {command}...", spinner="dots") as status:
            start_time = time.time()
            filtered_messages: list[str] = []
            pr_url: str | None = None
            error_message: str | None = None
            success = True

            # Stream events in real-time
            for event in executor.execute_command_streaming(
                command, worktree_path, dangerous, verbose=False
            ):
                if event.event_type == "text":
                    console.print(event.content)
                    filtered_messages.append(event.content)
                elif event.event_type == "tool":
                    console.print(event.content)
                    filtered_messages.append(event.content)
                elif event.event_type == "spinner_update":
                    # Update spinner text dynamically
                    status.update(event.content)
                elif event.event_type == "pr_url":
                    pr_url = event.content
                elif event.event_type == "error":
                    error_message = event.content
                    success = False

            duration = time.time() - start_time

            # Update spinner to final status
            final_status = "✅ Complete" if success else "❌ Failed"
            status.update(final_status)

            # Create result
            result = CommandResult(
                success=success,
                pr_url=pr_url,
                duration_seconds=duration,
                error_message=error_message,
                filtered_messages=filtered_messages,
            )

    return result


def execute_streaming_commands(
    executor: ClaudeExecutor,
    commands: list[str],
    worktree_path: Path,
    dangerous: bool,
    verbose: bool,
) -> list[CommandResult]:
    """Execute multiple Claude CLI commands in sequence with streaming output.

    Executes commands one at a time, stopping on first failure.
    Each command gets its own spinner/output section.

    Args:
        executor: ClaudeExecutor instance for command execution
        commands: List of slash commands to execute in order
        worktree_path: Path to worktree directory to run commands in
        dangerous: Whether to skip permission prompts
        verbose: Whether to show raw output (True) or filtered output (False)

    Returns:
        List of CommandResult objects, one per executed command.
        If a command fails, the list will be shorter than the input commands list.

    Raises:
        click.ClickException: If Claude CLI not found
    """
    # Verify Claude is available (once, before starting)
    if not executor.is_claude_available():
        raise click.ClickException(
            "Claude CLI not found\nInstall from: https://claude.com/download"
        )

    results: list[CommandResult] = []

    for cmd in commands:
        # Execute with streaming (availability already checked)
        result = _execute_single_command_streaming(executor, cmd, worktree_path, dangerous, verbose)
        results.append(result)

        # Stop on first failure
        if not result.success:
            break

    return results


def _execute_single_command_streaming(
    executor: ClaudeExecutor,
    command: str,
    worktree_path: Path,
    dangerous: bool,
    verbose: bool,
) -> CommandResult:
    """Execute single command (internal helper, no availability check).

    This is an internal helper that assumes Claude availability was already checked.
    Use execute_streaming_command() or execute_streaming_commands() for public API.
    """
    console = Console()

    if verbose:
        # Verbose mode - simple output, no spinner
        click.echo(f"Running {command}...", err=True)
        return executor.execute_command(command, worktree_path, dangerous, verbose=True)

    # Filtered mode - streaming with dynamic spinner updates
    with console.status(f"Running {command}...", spinner="dots") as status:
        start_time = time.time()
        filtered_messages: list[str] = []
        pr_url: str | None = None
        error_message: str | None = None
        success = True

        # Stream events in real-time
        for event in executor.execute_command_streaming(
            command, worktree_path, dangerous, verbose=False
        ):
            if event.event_type == "text":
                console.print(event.content)
                filtered_messages.append(event.content)
            elif event.event_type == "tool":
                console.print(event.content)
                filtered_messages.append(event.content)
            elif event.event_type == "spinner_update":
                # Update spinner text dynamically
                status.update(event.content)
            elif event.event_type == "pr_url":
                pr_url = event.content
            elif event.event_type == "error":
                error_message = event.content
                success = False

        duration = time.time() - start_time

        # Update spinner to final status
        final_status = "✅ Complete" if success else "❌ Failed"
        status.update(final_status)

        return CommandResult(
            success=success,
            pr_url=pr_url,
            duration_seconds=duration,
            error_message=error_message,
            filtered_messages=filtered_messages,
        )
