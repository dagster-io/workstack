"""GT kit operations for git, Graphite (gt), and GitHub (gh)."""

from erk_shared.integrations.gt.abc import GitGtKit, GitHubGtKit, GraphiteGtKit, GtKit
from erk_shared.integrations.gt.fake import (
    FakeGitGtKitOps,
    FakeGraphiteGtKitOps,
    FakeGtKitOps,
    GitHubState,
    GitState,
    GraphiteState,
)
from erk_shared.integrations.gt.github_adapter import GitHubAdapter
from erk_shared.integrations.gt.real import (
    RealGitGtKit,
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
    # Adapter
    "GitHubAdapter",
    # Fake implementations
    "FakeGtKitOps",
    "FakeGitGtKitOps",
    "FakeGraphiteGtKitOps",
    # State types
    "GitState",
    "GraphiteState",
    "GitHubState",
]
