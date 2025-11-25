"""Re-export from erk_shared for backward compatibility."""

from erk_shared.integrations.graphite.abc import Graphite

# Keep old name for compatibility
GraphiteIntegration = Graphite

__all__ = ["Graphite", "GraphiteIntegration"]
