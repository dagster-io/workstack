"""Rename forest command."""

import click

from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.forest_utils import rename_forest as rename_forest_util
from erk.core.forest_utils import validate_forest_name
from erk.core.repo_discovery import NoRepoSentinel


@click.command("rename", help="Rename a forest (label only, paths unchanged)")
@click.argument("old_name")
@click.argument("new_name")
@click.pass_obj
def rename_forest(ctx: ErkContext, old_name: str, new_name: str) -> None:
    """Rename a forest (label only, paths unchanged).

    This changes the forest label in metadata. Worktree paths remain unchanged.

    Args:
        old_name: Current forest name
        new_name: New forest name
    """
    if isinstance(ctx.repo, NoRepoSentinel):
        user_output(
            click.style("Error: ", fg="red")
            + "Not in a repository. This command requires a git repository."
        )
        raise SystemExit(1)

    # Validate new name
    if not validate_forest_name(new_name):
        user_output(
            click.style("Error: ", fg="red")
            + f"Invalid forest name: '{new_name}'\n\n"
            + "Forest names must be:\n"
            + "• Non-empty\n"
            + "• Max 30 characters\n"
            + "• Alphanumeric + hyphens only"
        )
        raise SystemExit(1)

    # Load forests
    metadata = ctx.forest_ops.load_forests()

    # Validate old_name exists
    if old_name not in metadata.forests:
        available = ", ".join(metadata.forests.keys()) if metadata.forests else "(none)"
        user_output(
            click.style("Error: ", fg="red")
            + f"Forest '{old_name}' does not exist\n\n"
            + f"Available forests: {available}"
        )
        raise SystemExit(1)

    # Validate new_name doesn't conflict
    if new_name in metadata.forests:
        user_output(
            click.style("Error: ", fg="red")
            + f"Forest '{new_name}' already exists\n\n"
            + "Choose a different name."
        )
        raise SystemExit(1)

    # Perform rename
    updated_metadata = rename_forest_util(metadata, old_name, new_name)

    # Save
    ctx.forest_ops.save_forests(updated_metadata)

    # Display success
    user_output(
        click.style("✓", fg="green")
        + f" Renamed forest '{click.style(old_name, fg='yellow')}' to "
        + f"'{click.style(new_name, fg='cyan', bold=True)}'"
    )
    user_output()
    user_output(
        click.style("Note: ", fg="white", dim=True)
        + "This only changes the forest label. Worktree paths remain unchanged."
    )
