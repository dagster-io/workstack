"""Scratch space for inter-process file passing.

Provides a `.tmp/` directory in the repository root for temporary files
that need to be readable by subagents without permission prompts.
"""

from erk_shared.scratch.scratch import (
    cleanup_stale_scratch,
    get_scratch_dir,
    write_scratch_file,
)

__all__ = [
    "get_scratch_dir",
    "write_scratch_file",
    "cleanup_stale_scratch",
]
