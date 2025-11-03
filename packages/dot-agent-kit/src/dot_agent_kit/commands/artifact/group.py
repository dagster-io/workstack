"""Artifact commands group."""

import click

from dot_agent_kit.commands.artifact import check, check_sync, list


@click.group()
def artifact_group() -> None:
    """Manage artifacts."""


# Register all artifact commands
artifact_group.add_command(list.list_cmd)
artifact_group.add_command(list.ls_cmd)
artifact_group.add_command(check.check)
artifact_group.add_command(check_sync.check_sync)
