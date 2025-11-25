"""Output utilities for CLI commands with clear intent."""

from erk_shared.output import format_duration, machine_output, user_output
from rich.panel import Panel
from rich.text import Text

from erk.core.claude_executor import CommandResult

__all__ = [
    "format_duration",
    "format_implement_summary",
    "machine_output",
    "user_output",
]


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
