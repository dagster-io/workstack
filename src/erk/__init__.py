"""workstack CLI entry point.

This package provides a Click-based CLI for managing git worktrees in a
global worktrees directory. See `workstack --help` for details.
"""

from erk.cli.cli import cli


def main() -> None:
    """CLI entry point used by the `workstack` console script."""
    cli()
