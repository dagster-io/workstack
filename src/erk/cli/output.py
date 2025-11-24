"""Output utilities for CLI commands with clear intent."""

from typing import Any

import click
from rich.panel import Panel
from rich.text import Text

from erk.core.claude_executor import CommandResult


def user_output(
    message: Any | None = None,
    nl: bool = True,
    color: bool | None = None,
) -> None:
    """Output informational message for human users.

    Routes to stderr so shell integration can capture structured data
    on stdout while users still see progress/status messages.

    Args:
        message: The string or bytes to output. Other objects are converted to strings.
        nl: Print a newline after the message. Enabled by default.
        color: Force showing or hiding colors and other styles. By default, Click
            will remove color if the output does not look like an interactive terminal.
    """
    click.echo(message, nl=nl, err=True, color=color)


def machine_output(
    message: Any | None = None,
    nl: bool = True,
    color: bool | None = None,
) -> None:
    """Output structured data for machine/script consumption.

    Routes to stdout for shell wrappers to capture. Should only be used
    for final output like activation script paths.

    Args:
        message: The string or bytes to output. Other objects are converted to strings.
        nl: Print a newline after the message. Enabled by default.
        color: Force showing or hiding colors and other styles. By default, Click
            will remove color if the output does not look like an interactive terminal.
    """
    click.echo(message, nl=nl, err=False, color=color)


def format_implement_summary(results: list[CommandResult], total_duration: float) -> Panel:
    """Format final summary box with status, PR link, timing, errors.

    Args:
        results: List of CommandResult from executed commands
        total_duration: Total execution time in seconds

    Returns:
        Rich Panel with formatted summary

    Example:
        >>> results = [CommandResult(success=True, pr_url="https://...", ...)]
        >>> panel = format_implement_summary(results, 123.45)
        >>> console.print(panel)
    """
    # Determine overall success
    overall_success = all(r.success for r in results)

    # Build summary lines
    lines: list[Text] = []

    # Status line
    if overall_success:
        lines.append(Text("✅ Status: Success", style="green"))
    else:
        lines.append(Text("❌ Status: Failed", style="red"))

    # Duration
    duration_str = format_duration(total_duration)
    lines.append(Text(f"⏱  Duration: {duration_str}"))

    # PR link (if any)
    pr_url: str | None = None
    for result in results:
        if result.pr_url:
            pr_url = result.pr_url
            break

    if pr_url:
        lines.append(Text(f"🔗 PR: {pr_url}", style="blue"))

    # Error details (if failed)
    if not overall_success:
        for i, result in enumerate(results):
            if not result.success:
                if result.error_message:
                    lines.append(Text(""))  # Blank line
                    lines.append(Text(f"Error in command {i + 1}:", style="red bold"))
                    lines.append(Text(result.error_message, style="red"))

    # Combine lines
    content = Text("\n").join(lines)

    # Create panel
    title = "Implementation Complete" if overall_success else "Implementation Failed"
    return Panel(
        content, title=title, border_style="green" if overall_success else "red", padding=(1, 2)
    )


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string (e.g., "2m 34s" or "45s")

    Example:
        >>> format_duration(154.5)
        '2m 34s'
        >>> format_duration(45.2)
        '45s'
    """
    if seconds < 60:
        return f"{seconds:.0f}s"

    minutes = int(seconds / 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes}m {remaining_seconds}s"
