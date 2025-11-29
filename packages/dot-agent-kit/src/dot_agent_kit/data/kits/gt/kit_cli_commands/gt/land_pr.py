"""Shim for land_pr kit CLI command.

The canonical implementation is in erk_shared.integrations.gt.kit_cli_commands.gt.land_pr.
This file exists only to provide the entry point for the kit CLI system.
Import symbols directly from the canonical location.
"""

from erk_shared.integrations.gt.kit_cli_commands.gt.land_pr import land_pr as land_pr
