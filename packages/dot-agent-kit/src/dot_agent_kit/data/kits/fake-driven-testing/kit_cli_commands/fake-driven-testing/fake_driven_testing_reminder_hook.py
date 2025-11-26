#!/usr/bin/env python3
"""Fake-Driven Testing Reminder Command."""

import click


@click.command()
def fake_driven_testing_reminder_hook() -> None:
    """Output fake-driven-testing reminder for UserPromptSubmit hook."""
    click.echo(
        "📌 fake-driven-testing: Load if not yet loaded this session (skills persist)\n"
        "\n"
        "WHY: 5-layer defense-in-depth strategy (see skill for architecture)\n"
        "NOTE: Guides test placement, fake usage, integration class architecture patterns"
    )


if __name__ == "__main__":
    fake_driven_testing_reminder_hook()
