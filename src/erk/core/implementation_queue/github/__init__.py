"""GitHub integration for implementation queue operations."""

from erk.core.implementation_queue.github.abc import GitHubAdmin
from erk.core.implementation_queue.github.dry_run import DryRunGitHubAdmin
from erk.core.implementation_queue.github.printing import PrintingGitHubAdmin
from erk.core.implementation_queue.github.real import RealGitHubAdmin

# Backward compatibility alias
NoopGitHubAdmin = DryRunGitHubAdmin

__all__ = [
    "GitHubAdmin",
    "RealGitHubAdmin",
    "DryRunGitHubAdmin",
    "NoopGitHubAdmin",
    "PrintingGitHubAdmin",
]
