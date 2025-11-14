#!/usr/bin/env python3
"""
Dignified Python Compliance Reminder Command

Outputs the dignified-python compliance reminder for UserPromptSubmit hook.
This command is invoked via dot-agent run dignified-python-310 compliance-reminder-hook.
"""

import click


@click.command()
def compliance_reminder_hook() -> None:
    """Output dignified-python compliance reminder for UserPromptSubmit hook."""
    click.echo(
        "🔴 DIGNIFIED PYTHON 3.10: Load dignified-python-310 skill when editing Python. "
        "STRICT compliance required."
    )


if __name__ == "__main__":
    compliance_reminder_hook()
