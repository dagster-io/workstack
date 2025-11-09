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
    click.echo("<reminder>")
    click.echo(
        "🔴 DIGNIFIED PYTHON 3.10: Load dignified-python-310 skill when editing Python. "
        "STRICT compliance required."
    )
    click.echo()
    click.echo("LBYL (Look Before You Leap) NOT EAFP (Easier to Ask Forgiveness than Permission)")
    click.echo("  • Check conditions FIRST: if key in dict, if path.exists(), if hasattr()")
    click.echo("  • NEVER use try/except for control flow")
    click.echo()
    click.echo("FORBIDDEN patterns (will be rejected):")
    click.echo("  • try/except for control flow → Use if key in dict, if path.exists(), etc.")
    click.echo("  • List[str], Optional, Union → Use list[str], str|None")
    click.echo("  • Relative imports (.module) → Use absolute (workstack.module)")
    click.echo("  • Silent fallbacks → Let exceptions bubble, fail fast")
    click.echo("  • from __future__ import annotations → Python 3.13+ doesn't need it")
    click.echo("</reminder>")


if __name__ == "__main__":
    compliance_reminder_hook()
