"""Re-export simple_submit command from erk-shared.

This module is a thin shim that re-exports the simple_submit command from its
canonical location in erk-shared. All implementation has been moved to
erk-shared/integrations/graphite/ for true canonicalization.
"""

from erk_shared.integrations.graphite.kit_cli_commands.gt.simple_submit import (
    DebugLogger,
    execute_simple_submit,
    simple_submit,
)

__all__ = ["DebugLogger", "execute_simple_submit", "simple_submit"]
