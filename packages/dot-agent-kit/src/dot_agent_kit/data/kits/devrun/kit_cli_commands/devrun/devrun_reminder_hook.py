#!/usr/bin/env python3
"""
Devrun Reminder Command

Outputs the devrun agent reminder for UserPromptSubmit hook.
This command is invoked via dot-agent run devrun devrun-reminder-hook.
"""

import click


@click.command()
def devrun_reminder_hook() -> None:
    """Output devrun agent reminder for UserPromptSubmit hook."""
    click.echo(
        "🛠️ Use devrun agent for pytest, pyright, ruff, prettier, make, gt (including uv run)"
    )


if __name__ == "__main__":
    devrun_reminder_hook()
