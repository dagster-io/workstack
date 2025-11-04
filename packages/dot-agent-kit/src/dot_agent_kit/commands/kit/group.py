"""Kit commands group."""

import click

from dot_agent_kit.commands.kit import install, search, sync
from dot_agent_kit.commands.kit.list import list_installed_kits, ls
from dot_agent_kit.commands.kit.remove import remove, rm


@click.group()
def kit_group() -> None:
    """Manage kits - install, update, sync, and search.

    Common commands:
      install    Install or update a specific kit
      list/ls    List installed kits
      remove/rm  Remove installed kits
      search     Search or list all available kits
      sync       Sync all or specific kits with their sources
    """


# Register all kit commands
kit_group.add_command(install.install)
kit_group.add_command(list_installed_kits)
kit_group.add_command(ls)
kit_group.add_command(remove)
kit_group.add_command(rm)
kit_group.add_command(search.search)
kit_group.add_command(sync.sync)
