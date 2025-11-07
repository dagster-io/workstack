"""Artifact command group."""

import click

from dot_agent_kit.commands.artifact.list import list_artifacts, ls
from dot_agent_kit.commands.artifact.show import show_artifact
from dot_agent_kit.commands.artifact.where import where_artifact


@click.group(name="artifact")
def artifact_group() -> None:
    """Manage and inspect Claude Code artifacts."""
    pass


# Register commands
artifact_group.add_command(list_artifacts)
artifact_group.add_command(ls)
artifact_group.add_command(show_artifact)
artifact_group.add_command(where_artifact)
