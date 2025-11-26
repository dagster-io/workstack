"""Experimental plan commands - subject to removal.

This module contains experimental features for the plan command group.
To remove all experimental features, delete this directory and update
the parent __init__.py to remove the import.

Related files (also delete if removing experiment):
  - .github/workflows/plan-create.yml
  - .claude/commands/erk/plan-remote.md
  - tests/commands/plan/experimental/
"""

from erk.cli.commands.plan.experimental.create_remote_cmd import create_remote_cmd

__all__ = ["create_remote_cmd"]
