"""Re-export from erk_shared for backward compatibility."""

from erk_shared.integrations.graphite.real import RealGraphite

# Keep old name for compatibility
RealGraphiteIntegration = RealGraphite

__all__ = ["RealGraphite", "RealGraphiteIntegration"]
