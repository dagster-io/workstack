"""GitHub implementation of plan storage.

This module re-exports from erk_shared.plan_store.github for backwards compatibility.
New code should import directly from erk_shared.plan_store.github.
"""

from erk_shared.plan_store.github import GitHubPlanStore

__all__ = ["GitHubPlanStore"]
