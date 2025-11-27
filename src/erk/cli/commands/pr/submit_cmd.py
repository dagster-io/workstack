"""Submit current branch as a pull request using Python orchestration.

This command orchestrates the PR submission workflow directly in Python,
using Claude only for what requires intelligence: generating commit messages.

Architecture:
    erk pr submit → Python orchestration
                    ├── execute_pre_analysis() (direct function call)
                    ├── get_diff_context() (direct function call)
                    ├── Claude CLI → /gt:generate-commit-message (AI-only)
                    ├── execute_post_analysis() (direct function call)
                    └── display results (Python)

Benefits:
    - No improvisation: Python controls all operations
    - Token efficiency: AI only sees diff, not orchestration context
    - Faster execution: No roundtrips between agent and tools
    - Deterministic: Mechanical operations are predictable
    - Testable: Can unit test orchestration without Claude
"""

import tempfile
from pathlib import Path

import click
from rich.console import Console

from erk.core.claude_executor import ClaudeExecutor
from erk.core.context import ErkContext
from erk.data.kits.gt.kit_cli_commands.gt.submit_branch import (
    DiffContextResult,
    PostAnalysisError,
    PostAnalysisResult,
    PreAnalysisError,
    execute_post_analysis,
    execute_pre_analysis,
    get_diff_context,
)


def _generate_commit_message(
    executor: ClaudeExecutor,
    diff_context: DiffContextResult,
    cwd: Path,
    dangerous: bool,
) -> str:
    """Call Claude to generate commit message from diff.

    Writes diff to temp file to handle large diffs without hitting
    context limits in the prompt.

    Args:
        executor: Claude CLI executor
        diff_context: Result from get_diff_context()
        cwd: Current working directory for Claude execution
        dangerous: Whether to skip permission prompts

    Returns:
        Generated commit message text
    """
    # Write diff to temp file (handles large diffs)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".diff", delete=False, encoding="utf-8"
    ) as f:
        f.write(f"Branch: {diff_context.current_branch}\n")
        f.write(f"Parent: {diff_context.parent_branch}\n\n")
        f.write(diff_context.diff)
        diff_file = Path(f.name)

    try:
        # Invoke minimal command that reads diff file
        prompt = f"/gt:generate-commit-message {diff_file}"
        result = executor.execute_command(prompt, cwd, dangerous)
        return "\n".join(result.filtered_messages)
    finally:
        diff_file.unlink(missing_ok=True)


def _display_success_results(
    console: Console,
    result: PostAnalysisResult,
) -> None:
    """Display success results from PR submission.

    Args:
        console: Rich console for output
        result: Success result from post-analysis
    """
    console.print()
    console.print("[bold]## Branch Submission Complete[/bold]")
    console.print()
    console.print("[bold]### What Was Done[/bold]")
    console.print()
    console.print("✓ Created commit with AI-generated message")
    console.print("✓ Submitted branch to Graphite")

    if result.pr_number is not None:
        console.print(f"✓ Updated PR #{result.pr_number}: {result.pr_title}")

    if result.issue_number is not None:
        console.print(f"✓ Linked to issue #{result.issue_number} (will auto-close on merge)")

    console.print()
    console.print("[bold]### View PR[/bold]")
    console.print()

    # Prefer Graphite URL, fall back to GitHub URL
    url = result.graphite_url if result.graphite_url else result.pr_url
    if url:
        console.print(url)


@click.command("submit")
@click.option("--dangerous", is_flag=True, help="Skip permission prompts")
@click.option("--verbose", is_flag=True, help="Show full Claude output")
@click.pass_obj
def pr_submit(ctx: ErkContext, dangerous: bool, verbose: bool) -> None:
    """Submit current branch as a pull request using Claude Code.

    Orchestrates the workflow in Python, using Claude only for
    generating the commit message from the diff analysis.

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
    cwd = ctx.cwd

    # Verify Claude is available
    if not executor.is_claude_available():
        raise click.ClickException(
            "Claude CLI not found\nInstall from: https://claude.com/download"
        )

    # Step 1: Pre-analysis (direct Python call)
    with console.status("Preparing branch...", spinner="dots"):
        pre_result = execute_pre_analysis()
        if isinstance(pre_result, PreAnalysisError):
            raise click.ClickException(
                f"{pre_result.message}\n\nError type: {pre_result.error_type}"
            )

    # Display pre-analysis status
    if verbose:
        click.echo(pre_result.message, err=True)

    # Step 2: Get diff context (direct Python call)
    with console.status("Analyzing changes...", spinner="dots"):
        try:
            diff_context = get_diff_context()
        except ValueError as e:
            raise click.ClickException(str(e)) from e

    # Step 3: Generate commit message (AI - the only Claude call)
    with console.status("Generating commit message...", spinner="dots"):
        commit_message = _generate_commit_message(
            executor,
            diff_context,
            cwd,
            dangerous,
        )

    if not commit_message.strip():
        raise click.ClickException("Failed to generate commit message")

    if verbose:
        click.echo("\n--- Generated Commit Message ---", err=True)
        click.echo(commit_message, err=True)
        click.echo("--- End Commit Message ---\n", err=True)

    # Step 4: Post-analysis (direct Python call)
    with console.status("Submitting PR...", spinner="dots"):
        post_result = execute_post_analysis(commit_message)
        if isinstance(post_result, PostAnalysisError):
            raise click.ClickException(
                f"{post_result.message}\n\nError type: {post_result.error_type}"
            )

    # Step 5: Display results (Python)
    _display_success_results(console, post_result)

    # Show PR URL prominently if created
    if post_result.pr_url:
        click.echo(f"\n🔗 PR: {post_result.pr_url}")
