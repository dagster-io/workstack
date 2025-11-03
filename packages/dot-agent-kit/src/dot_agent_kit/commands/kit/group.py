"""Kit commands group."""

import click

from dot_agent_kit.commands.kit import init, install, search, sync, update
from dot_agent_kit.commands.kit.list import list_installed_kits, ls
from dot_agent_kit.commands.kit.remove import remove, rm


@click.group()
def kit_group() -> None:
    """Manage kits and installations."""


# Register all kit commands
kit_group.add_command(init.init)
kit_group.add_command(install.install)
kit_group.add_command(list_installed_kits)
kit_group.add_command(ls)
kit_group.add_command(remove)
kit_group.add_command(rm)
kit_group.add_command(search.search)
kit_group.add_command(sync.sync)
kit_group.add_command(update.update)
