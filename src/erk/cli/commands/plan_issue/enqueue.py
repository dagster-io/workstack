"""Command to enqueue a plan issue for automatic implementation."""

import click

from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_repo_dir


@click.command("enqueue")
@click.argument("identifier", type=str)
@click.pass_obj
def enqueue_plan_issue(ctx: ErkContext, identifier: str) -> None:
    """Enqueue a plan issue for automatic implementation.

    This command adds the 'erk-queue' label to an existing plan issue,
    which triggers GitHub Actions to automatically create a branch and
    implement the plan.

    Args:
        identifier: Plan issue identifier (e.g., "42" for GitHub)

    Examples:
        erk plan-issue enqueue 42
        erk plan-issue enqueue github-123
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    repo_root = ensure_repo_dir(repo)

    # Fetch the plan issue to verify it exists
    try:
        plan_issue = ctx.plan_issue_store.get_plan_issue(repo_root, identifier)
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from e

    # Extract GitHub issue number from metadata
    if "number" not in plan_issue.metadata:
        user_output(
            click.style("Error: ", fg="red")
            + "Plan issue does not have a GitHub issue number in metadata"
        )
        raise SystemExit(1)

    # metadata["number"] is object type, but we know it should be int
    number_value = plan_issue.metadata["number"]
    if not isinstance(number_value, int):
        user_output(
            click.style("Error: ", fg="red") + f"Invalid issue number in metadata: {number_value}"
        )
        raise SystemExit(1)

    issue_number = number_value

    # Ensure erk-queue label exists in the repository
    try:
        ctx.issues.ensure_label_exists(
            repo_root,
            label="erk-queue",
            description="Implementation plan queued for automatic implementation",
            color="FFA500",
        )
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + f"Failed to ensure label exists: {e}")
        raise SystemExit(1) from e

    # Add erk-queue label to the issue
    try:
        ctx.issues.add_labels(repo_root, issue_number, ["erk-queue"])
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + f"Failed to add label: {e}")
        raise SystemExit(1) from e

    # Display success message
    issue_num_str = click.style(f"#{issue_number}", fg="cyan")
    label_str = click.style("erk-queue", fg="bright_magenta")
    success_str = click.style("✓", fg="green")

    user_output("")
    user_output(f"{success_str} Added {label_str} label to issue {issue_num_str}")
    user_output("")
    user_output(
        click.style("⚠️  Note:", fg="yellow")
        + " GitHub Actions will automatically create a branch and implement this plan."
    )
    user_output("    Monitor progress in the Actions tab of your repository.")
    user_output("")
