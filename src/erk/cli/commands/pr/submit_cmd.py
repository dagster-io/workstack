"""Submit current branch as a pull request using Claude Code."""

import click
from rich.console import Console

from erk.cli.claude_helpers import execute_streaming_command
from erk.core.context import ErkContext


@click.command("submit")
@click.option("--dangerous", is_flag=True, help="Skip permission prompts")
@click.option("--verbose", is_flag=True, help="Show full Claude output")
@click.pass_obj
def pr_submit(ctx: ErkContext, dangerous: bool, verbose: bool) -> None:
    """Submit current branch as a pull request using Claude Code.

    This command invokes Claude Code to execute the /gt:submit-pr slash command,
    which analyzes your changes and creates a pull request with Graphite.

    Examples:

    \b
      # Submit current branch as PR
      erk pr submit

    \b
      # Skip permission prompts
      erk pr submit --dangerous

    \b
      # Show full Claude output
      erk pr submit --verbose
    """
    result = execute_streaming_command(
        executor=ctx.claude_executor,
        command="/gt:submit-pr",
        worktree_path=ctx.cwd,
        dangerous=dangerous,
        verbose=verbose,
    )

    # Display PR URL if available
    if result.pr_url:
        console = Console()
        console.print(f"\n[bold green]PR created:[/bold green] {result.pr_url}")

    # Display error if failed
    if not result.success:
        if result.error_message:
            console = Console()
            console.print(f"\n[bold red]Error:[/bold red] {result.error_message}")
        raise click.ClickException("PR submission failed")
