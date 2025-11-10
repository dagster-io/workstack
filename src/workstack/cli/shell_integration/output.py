"""Shell integration output utilities.

Provides consistent output routing for commands that support --script mode.
"""

import click


def script_mode_echo(message: str, *, script_mode: bool, error: bool = False) -> None:
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
    click.echo(message, err=error or script_mode)
