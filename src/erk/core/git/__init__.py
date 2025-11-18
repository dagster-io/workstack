"""Git operations subpackage.

This subpackage provides abstractions over git operations with support for
testing via fakes and dry-run via wrappers.
"""

from erk.core.git.abc import Git, RerootResult, WorktreeInfo, find_worktree_for_branch
from erk.core.git.noop import NoopGit
from erk.core.git.printing import PrintingGit
from erk.core.git.real import RealGit

__all__ = [
    "Git",
    "WorktreeInfo",
    "RerootResult",
    "RealGit",
    "NoopGit",
    "PrintingGit",
    "find_worktree_for_branch",
]
