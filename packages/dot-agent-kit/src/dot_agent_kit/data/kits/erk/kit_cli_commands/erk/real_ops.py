"""Re-export real erk worktree implementations from erk-shared.

This module is a thin shim that re-exports real implementations from their
canonical location in erk-shared. All implementation lives in
erk-shared/integrations/erk_wt/ for true canonicalization.
"""

from erk_shared.integrations.erk_wt import RealErkWtKit

__all__ = ["RealErkWtKit"]
