"""Submit current branch as a pull request.

Calls orchestrate_submit_workflow() directly for immediate progress feedback.
"""

import click
from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import (
    PostAnalysisError,
    PostAnalysisResult,
    PreAnalysisError,
    orchestrate_submit_workflow,
)

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
    # Unused but kept for future extensibility
    _ = ctx

    # Call orchestrate_submit_workflow directly - immediate progress feedback
    result = orchestrate_submit_workflow()

    # Handle errors
    if isinstance(result, PreAnalysisError):
        error_msg = result.message
        if result.error_type == "gt_not_authenticated":
            error_msg = f"{result.message}\n\nRun 'gt auth' to authenticate with Graphite"
        elif result.error_type == "gh_not_authenticated":
            error_msg = f"{result.message}\n\nRun 'gh auth login' to authenticate with GitHub"
        elif result.error_type == "pr_has_conflicts":
            error_msg = f"{result.message}\n\nResolve conflicts before submitting"
        raise click.ClickException(error_msg)

    if isinstance(result, PostAnalysisError):
        error_msg = result.message
        if result.error_type == "claude_not_available":
            error_msg = f"{result.message}\n\nInstall from: https://claude.com/download"
        elif result.error_type == "submit_conflict":
            error_msg = f"{result.message}\n\nResolve conflicts and try again"
        elif result.error_type == "submit_empty_parent":
            error_msg = (
                f"{result.message}\n\nRun 'gt track --parent <trunk>' to reparent this branch"
            )
        raise click.ClickException(error_msg)

    # Success - show PR URL prominently
    success_result: PostAnalysisResult = result
    click.echo(f"\n🔗 PR: {success_result.pr_url}")
    if success_result.graphite_url:
        click.echo(f"📊 Graphite: {success_result.graphite_url}")
