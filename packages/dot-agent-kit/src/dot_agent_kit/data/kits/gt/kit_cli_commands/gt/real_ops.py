"""Re-export real GT kit implementations from erk-shared.

This module is a thin shim that re-exports real implementations from their
canonical location in erk-shared. All implementation has been moved to
erk-shared/integrations/gt/ for true canonicalization.
"""

from erk_shared.integrations.gt import (
    GitHubAdapter,
    RealGitGtKit,
    RealGraphiteGtKit,
    RealGtKit,
)

__all__ = ["RealGtKit", "RealGitGtKit", "RealGraphiteGtKit", "GitHubAdapter"]
