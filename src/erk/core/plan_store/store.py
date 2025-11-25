"""Abstract interface for plan storage providers.

This module re-exports from erk_shared.plan_store.store for backwards compatibility.
New code should import directly from erk_shared.plan_store.store.
"""

from erk_shared.plan_store.store import PlanStore

__all__ = ["PlanStore"]
