"""Re-export submit_branch command from erk-shared.

This module is a thin shim that re-exports the submit_branch command from its
canonical location in erk-shared. All implementation has been moved to
erk-shared/integrations/graphite/ for true canonicalization.
"""

from erk_shared.integrations.graphite.kit_cli_commands.gt.submit_branch import (
    execute_post_analysis,
    execute_pre_analysis,
    get_diff_context,
    orchestrate_submit_workflow,
    pr_submit,
)

__all__ = [
    "execute_pre_analysis",
    "execute_post_analysis",
    "get_diff_context",
    "orchestrate_submit_workflow",
    "pr_submit",
]
