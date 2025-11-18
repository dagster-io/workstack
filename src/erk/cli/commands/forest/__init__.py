"""Forest command group for managing worktree collections."""

import click

# TODO: Implement forest subcommands
# from erk.cli.commands.forest.list import list_forests
# from erk.cli.commands.forest.merge import merge_forest
# from erk.cli.commands.forest.rename import rename_forest
# from erk.cli.commands.forest.reroot import reroot_forest
# from erk.cli.commands.forest.show import show_forest
# from erk.cli.commands.forest.show_current import show_current_forest
# from erk.cli.commands.forest.split import split_forest


@click.group("forest", invoke_without_command=True)
@click.pass_context
def forest_group(ctx: click.Context) -> None:
    """Manage forest collections of worktrees.

    Forests are named collections of worktrees belonging to the same Graphite stack.
    They enable unified stack management operations like split, merge, and reroot.

    When called without a subcommand, shows the forest for the current worktree.
    """
    # If no subcommand is provided, show placeholder message
    if ctx.invoked_subcommand is None:
        click.echo("Forest command infrastructure in progress.")
        click.echo("Subcommands will be available in a future release.")


# Register subcommands (TODO: uncomment when implemented)
# forest_group.add_command(list_forests)
# forest_group.add_command(show_forest)
# forest_group.add_command(rename_forest)
# forest_group.add_command(split_forest)
# forest_group.add_command(merge_forest)
# forest_group.add_command(reroot_forest)
