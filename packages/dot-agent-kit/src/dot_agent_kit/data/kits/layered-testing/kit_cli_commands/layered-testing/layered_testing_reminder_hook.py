#!/usr/bin/env python3
"""Layered Testing Reminder Command."""

import click


@click.command()
def layered_testing_reminder_hook() -> None:
    """Output layered-testing reminder for UserPromptSubmit hook."""
    click.echo(
        "🔴 LOAD layered-testing skill when writing tests, fixing bugs, adding features, "
        "or modifying ops layer\n"
        "\n"
        "WHY: 4-layer defense-in-depth strategy (fakes → mocked real → business logic → e2e)\n"
        "NOTE: Guides test placement, fake usage, ops architecture patterns"
    )


if __name__ == "__main__":
    layered_testing_reminder_hook()
