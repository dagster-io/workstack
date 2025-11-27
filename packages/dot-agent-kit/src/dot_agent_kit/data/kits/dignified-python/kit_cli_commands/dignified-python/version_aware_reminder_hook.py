#!/usr/bin/env python3
"""
Dignified Python Version-Aware Compliance Reminder Command

Detects the Python version at runtime and outputs the appropriate
dignified-python compliance reminder for UserPromptSubmit hook.
"""

import sys

import click


@click.command()
def version_aware_reminder_hook() -> None:
    """Output dignified-python compliance reminder with detected Python version."""
    # Detect Python version from runtime
    major = sys.version_info.major
    minor = sys.version_info.minor

    if major != 3:
        raise RuntimeError(f"Dignified Python requires Python 3.x, got Python {major}.{minor}")

    # Version-specific message
    version_code = f"3{minor}"
    skill_name = f"dignified-python-{version_code}"
    click.echo(
        f"📌 {skill_name}: Check if already loaded (look for 'skill is loading' message)\n"
        f"   ↳ If NOT loaded and writing Python: Load skill now\n"
        f"   ↳ If already loaded or not writing Python: Continue\n"
        "\n"
        f"WHY: LBYL compliance, Python 3.{minor}+ types, ABC interfaces\n"
        "NOTE: Skills persist entire session - load once, use throughout"
    )


if __name__ == "__main__":
    version_aware_reminder_hook()
