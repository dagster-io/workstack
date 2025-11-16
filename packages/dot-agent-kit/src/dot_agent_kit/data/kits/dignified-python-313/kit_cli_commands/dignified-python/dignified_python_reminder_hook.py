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
        "🔴 CRITICAL: LOAD dignified-python skill NOW before editing Python\n"
        "\n"
        "WHY: Ensures LBYL compliance, Python 3.13+ types, ABC interfaces\n"
        "NOTE: Checklist rules are EXCERPTS - skill contains complete philosophy & rationale"
    )


if __name__ == "__main__":
    dignified_python_reminder_hook()
