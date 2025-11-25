from erk_shared.integrations.time.abc import Time
from erk_shared.integrations.time.real import RealTime

# Aliases for backward compatibility
TimeIntegration = Time
RealTimeIntegration = RealTime

__all__ = [
    "RealTime",
    "RealTimeIntegration",
    "Time",
    "TimeIntegration",
]
