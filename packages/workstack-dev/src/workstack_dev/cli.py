"""Static CLI definition for workstack-dev.

This module uses static imports instead of dynamic command loading to enable
shell completion. Click's completion mechanism requires all commands to be
available at import time for inspection.
"""

import click

from workstack_dev.commands.branch_commit_count.command import branch_commit_count_command
from workstack_dev.commands.clean_cache.command import clean_cache_command
from workstack_dev.commands.codex_review.command import codex_review_command
from workstack_dev.commands.completion.command import completion_command
from workstack_dev.commands.create_agents_symlinks.command import create_agents_symlinks_command
from workstack_dev.commands.publish_to_pypi.command import publish_to_pypi_command
from workstack_dev.commands.reserve_pypi_name.command import reserve_pypi_name_command
from workstack_dev.commands.slash_command.command import slash_command_command

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(name="workstack-dev", context_settings=CONTEXT_SETTINGS)
def cli() -> None:
    """Development tools for workstack."""
    pass


# Register all commands
cli.add_command(branch_commit_count_command)
cli.add_command(clean_cache_command)
cli.add_command(codex_review_command)
cli.add_command(completion_command)
cli.add_command(create_agents_symlinks_command)
cli.add_command(publish_to_pypi_command)
cli.add_command(reserve_pypi_name_command)
cli.add_command(slash_command_command)
