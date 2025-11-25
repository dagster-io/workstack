"""Core types for provider-agnostic plan storage.

This module re-exports from erk_shared.plan_store.types for backwards compatibility.
New code should import directly from erk_shared.plan_store.types.
"""

from erk_shared.plan_store.types import Plan, PlanQuery, PlanState

__all__ = ["Plan", "PlanQuery", "PlanState"]
