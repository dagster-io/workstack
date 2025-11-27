#!/usr/bin/env python3
"""Fake-Driven Testing Reminder Command."""

import click


@click.command()
def fake_driven_testing_reminder_hook() -> None:
    """Output fake-driven-testing reminder for UserPromptSubmit hook."""
    click.echo(
        "📌 fake-driven-testing: Check if already loaded (look for 'skill is loading' message)\n"
        "   ↳ If NOT loaded and writing tests: Load skill now\n"
        "   ↳ If already loaded or not writing tests: Continue\n"
        "\n"
        "WHY: 5-layer defense-in-depth testing strategy\n"
        "NOTE: Skills persist entire session - load once, use throughout"
    )


if __name__ == "__main__":
    fake_driven_testing_reminder_hook()
