"""List all forests command."""

from datetime import datetime

import click

from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, RepoContext


def format_date(iso_timestamp: str) -> str:
    """Format ISO 8601 timestamp to human-readable date.

    Args:
        iso_timestamp: ISO 8601 format timestamp

    Returns:
        Formatted date like "2024-01-15"
    """
    dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    return dt.strftime("%Y-%m-%d")


@click.command("list", help="List all forests in repository")
@click.pass_obj
def list_forests(ctx: ErkContext) -> None:
    """List all forests in repository.

    Displays forest name, worktree count, and creation date.
    Sorted by creation date (newest first).
    """
    if isinstance(ctx.repo, NoRepoSentinel):
        user_output(
            click.style("Error: ", fg="red")
            + "Not in a repository. This command requires a git repository."
        )
        raise SystemExit(1)

    # Load forests
    metadata = ctx.forest_ops.load_forests()

    if not metadata.forests:
        user_output("No forests in repository.")
        raise SystemExit(0)

    # Get repository name for header
    repo: RepoContext = ctx.repo  # Type narrowing
    repo_name = repo.root.name

    # Sort forests by creation date (newest first)
    sorted_forests = sorted(metadata.forests.values(), key=lambda f: f.created_at, reverse=True)

    # Display header
    user_output(f"Forests in {click.style(repo_name, bold=True)}:")

    # Display each forest
    for forest in sorted_forests:
        forest_name = click.style(forest.name, fg="cyan", bold=True)
        count = f"({len(forest.worktrees)} worktrees)"
        date = f"created {format_date(forest.created_at)}"

        user_output(f"• {forest_name} {count} - {date}")
