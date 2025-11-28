"""Re-export pr_update command from erk-shared.

This module is a thin shim that re-exports the pr_update command from its
canonical location in erk-shared. All implementation has been moved to
erk-shared/integrations/gt/ for true canonicalization.
"""

from erk_shared.integrations.gt.kit_cli_commands.gt.pr_update import (
    execute_update_pr,
    pr_update,
)

__all__ = ["execute_update_pr", "pr_update"]
