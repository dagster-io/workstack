"""In-memory fake implementation for plan storage.

This module re-exports from erk_shared.plan_store.fake for backwards compatibility.
New code should import directly from erk_shared.plan_store.fake.
"""

from erk_shared.plan_store.fake import FakePlanStore

__all__ = ["FakePlanStore"]
