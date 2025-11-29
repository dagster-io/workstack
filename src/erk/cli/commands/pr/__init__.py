"""PR management commands."""

import click

from erk.cli.commands.pr.checkout_cmd import pr_checkout
from erk.cli.commands.pr.land_cmd import pr_land
from erk.cli.commands.pr.submit_cmd import pr_submit


@click.group("pr")
def pr_group() -> None:
    """Manage pull requests."""
    pass


pr_group.add_command(pr_checkout, name="checkout")
pr_group.add_command(pr_land, name="land")
pr_group.add_command(pr_submit, name="submit")
