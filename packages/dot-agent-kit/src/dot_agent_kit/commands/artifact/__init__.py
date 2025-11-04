"""Artifact inspection commands."""

import click

from dot_agent_kit.commands.artifact.list import list_cmd
from dot_agent_kit.commands.artifact.show import show
from dot_agent_kit.commands.artifact.where import where


@click.group()
def artifact() -> None:
    """Manage and inspect Claude artifacts."""
    pass


# Register commands
artifact.add_command(list_cmd)
artifact.add_command(show)
artifact.add_command(where)
