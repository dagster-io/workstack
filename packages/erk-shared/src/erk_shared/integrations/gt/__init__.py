"""GT kit operations for git, Graphite (gt), and GitHub (gh)."""

from erk_shared.integrations.gt.abc import GitGtKit, GitHubGtKit, GtKit
from erk_shared.integrations.gt.fake import (
    FakeGitGtKitOps,
    FakeGitHubGtKitOps,
    FakeGtKitOps,
    GitHubState,
    GitState,
)
from erk_shared.integrations.gt.real import (
    RealGitGtKit,
    RealGitHubGtKit,
    RealGtKit,
)
from erk_shared.integrations.gt.types import CommandResult

__all__ = [
    # ABC interfaces
    "GtKit",
    "GitGtKit",
    "GitHubGtKit",
    "CommandResult",
    # Real implementations
    "RealGtKit",
    "RealGitGtKit",
    "RealGitHubGtKit",
    # Fake implementations
    "FakeGtKitOps",
    "FakeGitGtKitOps",
    "FakeGitHubGtKitOps",
    # State types
    "GitState",
    "GitHubState",
]
