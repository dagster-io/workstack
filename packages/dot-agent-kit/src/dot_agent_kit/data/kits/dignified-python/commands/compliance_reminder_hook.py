#!/usr/bin/env python3
"""
Dignified Python Compliance Reminder Command

Outputs the dignified-python compliance reminder for UserPromptSubmit hook.
This command is invoked via dot-agent run dignified-python compliance-reminder-hook.
"""

import click


@click.command()
def compliance_reminder_hook() -> None:
    """Output dignified-python compliance reminder for UserPromptSubmit hook."""
    click.echo("<reminder>")
    click.echo(
        "CRITICAL: Load dignified-python skill when editing Python and "
        "strictly abide by the standards defined in it."
    )
    click.echo()
    click.echo("Core philosophy:")
    click.echo("  - Explicit, predictable code that fails fast")
    click.echo("  - LBYL over EAFP - check before acting")
    click.echo("  - Python 3.13+ syntax only")
    click.echo("  - Error boundaries at CLI/API level")
    click.echo()
    click.echo("Critical rules:")
    click.echo("  1. Exceptions: LBYL over EAFP 🔴")
    click.echo(
        "     - ALWAYS use LBYL (Look Before You Leap) first, before EAFP, "
        "which should be used only if absolutely necessary "
        "(only API supported by 3rd party library, for example)"
    )
    click.echo("     - Check conditions with if statements before acting")
    click.echo("     - Only handle exceptions at error boundaries (CLI, third-party APIs)")
    click.echo("     - Let exceptions bubble up by default")
    click.echo(
        "  2. Types: Use list[str], dict[str,int], str|None. FORBIDDEN: List, Optional, Union 🔴"
    )
    click.echo("  3. Imports: Absolute only. NEVER relative imports 🔴")
    click.echo("  4. Style: Max 4 indent levels. Extract helpers if deeper")
    click.echo("  5. Data: Prefer immutable data structures. Default to @dataclass(frozen=True)")
    click.echo("  6. NO fallback behavior: Fail fast, don't silently degrade 🔴")
    click.echo()
    click.echo("See full skill for details")
    click.echo("</reminder>")


if __name__ == "__main__":
    compliance_reminder_hook()
