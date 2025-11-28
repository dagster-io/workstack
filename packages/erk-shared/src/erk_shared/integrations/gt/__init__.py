"""GT kit operations for git, Graphite (gt), and GitHub (gh)."""

from erk_shared.integrations.gt.abc import GitGtKit, GitHubGtKit, GraphiteGtKit, GtKit
from erk_shared.integrations.gt.fake import (
    FakeGitGtKitOps,
    FakeGitHubGtKitOps,
    FakeGraphiteGtKitOps,
    FakeGtKitOps,
    GitHubState,
    GitState,
    GraphiteState,
)
from erk_shared.integrations.gt.real import (
    RealGitGtKit,
    RealGitHubGtKit,
    RealGraphiteGtKit,
    RealGtKit,
)
from erk_shared.integrations.gt.types import CommandResult

__all__ = [
    # ABC interfaces
    "GtKit",
    "GitGtKit",
    "GraphiteGtKit",
    "GitHubGtKit",
    "CommandResult",
    # Real implementations
    "RealGtKit",
    "RealGitGtKit",
    "RealGraphiteGtKit",
    "RealGitHubGtKit",
    # Fake implementations
    "FakeGtKitOps",
    "FakeGitGtKitOps",
    "FakeGraphiteGtKitOps",
    "FakeGitHubGtKitOps",
    # State types
    "GitState",
    "GraphiteState",
    "GitHubState",
]
