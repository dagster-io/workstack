"""Low-level output formatting primitives for land-stack."""

import click
from erk_shared.output.output import machine_output, user_output


def _emit(message: str, *, script_mode: bool, error: bool = False) -> None:
    """Emit a message to stdout or stderr based on script mode.

    In script mode, ALL output goes to stderr (so the shell wrapper can capture
    only the activation script from stdout). The `error` parameter has no effect
    in script mode since everything is already sent to stderr.

    In non-script mode, output goes to stdout by default, unless `error=True`.

    Args:
        message: Text to output.
        script_mode: True when running in --script mode (all output to stderr).
        error: Force stderr output in non-script mode (ignored in script mode).
    """
    if error or script_mode:
        user_output(message)
    else:
        machine_output(message)


def _format_cli_command(cmd: str, check: str) -> str:
    """Format a CLI command operation for display.

    Args:
        cmd: The CLI command string (e.g., "git checkout main")
        check: Checkmark string to append

    Returns:
        Formatted operation string with styling
    """
    cmd_styled = click.style(cmd, fg="white", dim=True)
    return f"  {cmd_styled} {check}"


def _format_description(description: str, check: str) -> str:
    """Format an internal operation description for display.

    Args:
        description: Description text (will be wrapped in brackets)
        check: Checkmark string to append

    Returns:
        Formatted description string with dim styling
    """
    desc_styled = click.style(f"[{description}]", dim=True)
    return f"  {desc_styled} {check}"
