"""Re-export erk worktree operations from erk-shared.

This module is a thin shim that re-exports erk worktree operations from their
canonical location in erk-shared. All implementation lives in
erk-shared/integrations/erk_wt/ for true canonicalization.
"""

from erk_shared.integrations.erk_wt import (
    ErkWtKit,
    IssueData,
    IssueParseResult,
    WorktreeCreationResult,
)

__all__ = ["ErkWtKit", "IssueData", "IssueParseResult", "WorktreeCreationResult"]
