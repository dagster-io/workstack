"""Submit current branch as a pull request using Claude Code."""

import time

import click
from rich.console import Console

from erk.cli.output import format_implement_summary
from erk.core.claude_executor import ClaudeExecutor, CommandResult
from erk.core.context import ErkContext


def _execute_streaming_submit(
    executor: ClaudeExecutor,
    worktree_path: str,
    dangerous: bool,
    verbose: bool,
    console: Console,
) -> CommandResult:
    """Execute /gt:pr-submit command with streaming output.

    Args:
        executor: Claude CLI executor
        worktree_path: Path to worktree directory
        dangerous: Whether to skip permission prompts
        verbose: Whether to show full output
        console: Rich console for output

    Returns:
        CommandResult with success status and PR URL if created
    """
    from pathlib import Path

    command = "/gt:pr-submit"

    if verbose:
        click.echo(f"Running {command}...", err=True)
        return executor.execute_command(command, Path(worktree_path), dangerous, verbose=True)

    # Filtered mode - streaming with spinner
    with console.status(f"Running {command}...", spinner="dots") as status:
        start_time = time.time()
        filtered_messages: list[str] = []
        pr_url: str | None = None
        pr_number: int | None = None
        pr_title: str | None = None
        issue_number: int | None = None
        error_message: str | None = None
        success = True

        for event in executor.execute_command_streaming(
            command, Path(worktree_path), dangerous, verbose=False
        ):
            if event.event_type == "text":
                console.print(event.content)
                filtered_messages.append(event.content)
            elif event.event_type == "tool":
                console.print(event.content)
                filtered_messages.append(event.content)
            elif event.event_type == "spinner_update":
                status.update(event.content)
            elif event.event_type == "pr_url":
                pr_url = event.content
            elif event.event_type == "pr_number":
                # Convert string back to int - safe because we control the source
                if event.content.isdigit():
                    pr_number = int(event.content)
            elif event.event_type == "pr_title":
                pr_title = event.content
            elif event.event_type == "issue_number":
                # Convert string back to int - safe because we control the source
                if event.content.isdigit():
                    issue_number = int(event.content)
            elif event.event_type == "error":
                error_message = event.content
                success = False

        duration = time.time() - start_time

        final_status = "✅ Complete" if success else "❌ Failed"
        status.update(final_status)

        return CommandResult(
            success=success,
            pr_url=pr_url,
            pr_number=pr_number,
            pr_title=pr_title,
            issue_number=issue_number,
            duration_seconds=duration,
            error_message=error_message,
            filtered_messages=filtered_messages,
        )


@click.command("submit")
@click.option("--dangerous", is_flag=True, help="Skip permission prompts")
@click.option("--verbose", is_flag=True, help="Show full Claude output")
@click.pass_obj
def pr_submit(ctx: ErkContext, dangerous: bool, verbose: bool) -> None:
    """Submit current branch as a pull request using Claude Code.

    Invokes Claude Code to execute the /gt:pr-submit slash command,
    which analyzes your changes, generates a commit message, and
    creates a pull request.

    Examples:

    \b
      # Submit PR with default settings
      erk pr submit

    \b
      # Submit PR without permission prompts
      erk pr submit --dangerous

    \b
      # Show full Claude output
      erk pr submit --verbose
    """
    executor = ctx.claude_executor
    console = Console()

    # Verify Claude is available
    if not executor.is_claude_available():
        raise click.ClickException(
            "Claude CLI not found\nInstall from: https://claude.com/download"
        )

    # Get current working directory (worktree path)
    worktree_path = str(ctx.cwd)

    # Execute the submit command
    start_time = time.time()
    result = _execute_streaming_submit(
        executor=executor,
        worktree_path=worktree_path,
        dangerous=dangerous,
        verbose=verbose,
        console=console,
    )

    # Show summary (unless verbose mode)
    if not verbose:
        total_duration = time.time() - start_time
        summary = format_implement_summary([result], total_duration)
        console.print(summary)

    # Show PR URL prominently if created
    if result.pr_url:
        click.echo(f"\n🔗 PR: {result.pr_url}")

    # Raise exception if command failed
    if not result.success:
        raise click.ClickException(result.error_message or "PR submission failed")
