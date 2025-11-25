"""Re-export from erk_shared for backward compatibility."""

from erk_shared.integrations.time.real import RealTime

# Keep old name for compatibility
RealTimeIntegration = RealTime

__all__ = ["RealTime", "RealTimeIntegration"]
