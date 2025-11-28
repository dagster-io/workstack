"""Re-export GT kit prompts from erk-shared.

This module is a thin shim that re-exports prompts from their canonical
location in erk-shared. All implementation has been moved to
erk-shared/integrations/gt/ for true canonicalization.
"""

from erk_shared.integrations.gt.prompts import (
    COMMIT_MESSAGE_SYSTEM_PROMPT,
    MAX_DIFF_CHARS,
    truncate_diff,
)

__all__ = ["COMMIT_MESSAGE_SYSTEM_PROMPT", "MAX_DIFF_CHARS", "truncate_diff"]
