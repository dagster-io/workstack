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
        "🔴 CRITICAL: For pytest/pyright/ruff/prettier/make/gt → MUST use devrun agent "
        '(Task tool with subagent_type="devrun"), NOT direct Bash\n'
        "\n"
        "This includes uv run variants: uv run pytest, uv run pyright, uv run ruff, etc.\n"
        "\n"
        "WHY: Specialized parsing & cost efficiency"
    )


if __name__ == "__main__":
    devrun_reminder_hook()
