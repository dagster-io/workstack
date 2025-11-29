"""Re-export GT kit operations from erk-shared.

This module is a thin shim that re-exports GT kit operations from their
canonical location in erk-shared. All implementation has been moved to
erk-shared/integrations/gt/ for true canonicalization.
"""

from erk_shared.integrations.gt import (
    CommandResult,
    GitGtKit,
    GitHubGtKit,
    GtKit,
)

__all__ = ["GtKit", "GitGtKit", "GitHubGtKit", "CommandResult"]
