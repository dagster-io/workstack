"""Re-export submit_branch command from erk-shared.

This module is a thin shim that re-exports the submit_branch command from its
canonical location in erk-shared. All implementation has been moved to
erk-shared/integrations/gt/ for true canonicalization.
"""

from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import (
    execute_finalize,
    execute_pre_analysis,
    execute_preflight,
    pr_submit,
)

__all__ = [
    "execute_pre_analysis",
    "execute_preflight",
    "execute_finalize",
    "pr_submit",
]
