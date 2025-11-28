"""Submit current branch as a pull request.

Delegates to the /gt:pr-submit slash command via Claude CLI.
"""

import json
from pathlib import Path

import click
from erk_shared.output.output import user_output

from erk.core.context import ErkContext


@click.command("submit")
@click.pass_obj
def pr_submit(ctx: ErkContext) -> None:
    """Submit current branch as a pull request.

    Analyzes your changes, generates a commit message via AI, and
    creates a pull request using Graphite.

    Examples:

    \b
      # Submit PR
      erk pr submit
    """
    executor = ctx.claude_executor

    # Verify Claude is available
    if not executor.is_claude_available():
        raise click.ClickException(
            "Claude CLI not found\n\nInstall from: https://claude.com/download"
        )

    # Execute the slash command with streaming output
    user_output("Submitting PR via Claude...")
    user_output("Launching Claude process (this may take up to 30 seconds)...")
    worktree_path = Path.cwd()

    # Track results from streaming events
    pr_url: str | None = None
    error_message: str | None = None
    success = True

    # Stream events and log each as JSON
    for event in executor.execute_command_streaming(
        command="/gt:pr-submit",
        worktree_path=worktree_path,
        dangerous=False,
    ):
        # Log each event as JSON for visibility
        event_json = json.dumps({"type": event.event_type, "content": event.content})
        click.echo(event_json)

        # Capture important data
        if event.event_type == "pr_url":
            pr_url = event.content
        elif event.event_type == "error":
            error_message = event.content
            success = False

    # Display PR URL on success
    if pr_url:
        click.echo(f"\n🔗 PR: {pr_url}")

    if not success:
        error_msg = error_message or "PR submission failed"
        raise click.ClickException(error_msg)
