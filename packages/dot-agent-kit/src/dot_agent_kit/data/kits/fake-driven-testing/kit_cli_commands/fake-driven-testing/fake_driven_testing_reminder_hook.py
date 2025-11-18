#!/usr/bin/env python3
"""Fake-Driven Testing Reminder Command."""

import click


@click.command()
def fake_driven_testing_reminder_hook() -> None:
    """Output fake-driven-testing reminder for UserPromptSubmit hook."""
    click.echo(
        "🔴 CRITICAL: LOAD fake-driven-testing skill NOW before editing Python\n"
        "\n"
        "WHY: 4-layer defense-in-depth strategy (fakes → mocked real → business logic → e2e)\n"
        "NOTE: Guides test placement, fake usage, integration class architecture patterns"
    )


if __name__ == "__main__":
    fake_driven_testing_reminder_hook()
