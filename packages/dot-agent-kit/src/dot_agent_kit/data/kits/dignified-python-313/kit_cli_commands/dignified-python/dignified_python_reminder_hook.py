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
    click.echo(
        "🔴 Load dignified-python-313 skill when editing Python "
        "(LBYL: check conditions first, never try/except for control flow)"
    )


if __name__ == "__main__":
    dignified_python_reminder_hook()
