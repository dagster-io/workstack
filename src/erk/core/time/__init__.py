"""Time operations abstraction for testing.

NOTE: Implementation moved to erk_shared.integrations.time.
This module re-exports for backward compatibility.
"""

from erk_shared.integrations.time import (
    RealTime,
    RealTimeIntegration,
    Time,
    TimeIntegration,
)

__all__ = [
    "RealTime",
    "RealTimeIntegration",
    "Time",
    "TimeIntegration",
]
