"""Re-export from erk_shared for backward compatibility."""

from erk_shared.integrations.time.abc import Time

# Keep old name for compatibility
TimeIntegration = Time

__all__ = ["Time", "TimeIntegration"]
