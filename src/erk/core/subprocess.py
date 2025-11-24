"""Subprocess execution with rich error context - re-exported from erk-shared.

This module re-exports run_subprocess_with_context from erk-shared.
The implementation has been moved to erk-shared to allow both erk and dot-agent-kit
to use the same subprocess wrapper without circular dependencies.

For the actual implementation, see: erk-shared/src/erk_shared/subprocess_utils.py
"""

# Re-export from erk-shared
from erk_shared.subprocess_utils import run_subprocess_with_context  # noqa: F401

__all__ = ["run_subprocess_with_context"]
