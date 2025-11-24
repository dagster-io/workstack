#!/usr/bin/env python3
"""
Session ID Injector Hook

Injects the current session ID into conversation context for /erk:enhance-and-save-plan.
This command is invoked via dot-agent run erk session-id-injector-hook.
"""

import json
import sys

import click


@click.command(name="session-id-injector-hook")
def session_id_injector_hook() -> None:
    """Inject session ID into conversation context when relevant."""
    # Attempt to read session context from stdin (if Claude Code provides it)
    session_id = None

    try:
        # Check if stdin has data (non-blocking)
        if not sys.stdin.isatty():
            stdin_data = sys.stdin.read().strip()
            if stdin_data:
                context = json.loads(stdin_data)
                session_id = context.get("session_id")
    except (json.JSONDecodeError, Exception):
        # If stdin reading fails, continue without session ID
        pass

    # Output session ID if available
    if session_id:
        click.echo("<reminder>")
        click.echo(f"SESSION_CONTEXT: session_id={session_id}")
        click.echo("</reminder>")
    # If no session ID available, output nothing (hook doesn't fire unnecessarily)


if __name__ == "__main__":
    session_id_injector_hook()
