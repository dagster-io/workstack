"""Re-export real GT kit implementations from erk-shared.

This module is a thin shim that re-exports real implementations from their
canonical location in erk-shared. All implementation has been moved to
erk-shared/integrations/gt/ for true canonicalization.
"""

from erk_shared.integrations.gt import (
    RealGitGtKit,
    RealGitHubGtKit,
    RealGtKit,
)

__all__ = ["RealGtKit", "RealGitGtKit", "RealGitHubGtKit"]
