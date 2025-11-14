#!/usr/bin/env python3
"""
Dignified Python Compliance Reminder Command

Outputs the dignified-python compliance reminder for UserPromptSubmit hook.
This command is invoked via dot-agent run dignified-python-313 compliance-reminder-hook.
"""

import click


@click.command()
def dignified_python_reminder_hook() -> None:
    """Output dignified-python compliance reminder for UserPromptSubmit hook."""
    click.echo("<reminder>")
    click.echo(
        "🔴 Dignified Python 3.13+: Load dignified-python-313 skill when editing Python. "
        "Strict compliance required."
    )
    click.echo()
    click.echo("Look Before You Leap, not Easier to Ask Forgiveness than Permission")
    click.echo("  • Check conditions first: if key in dict, if path.exists(), if hasattr()")
    click.echo("  • Never use try/except for control flow")
    click.echo("</reminder>")


if __name__ == "__main__":
    dignified_python_reminder_hook()
