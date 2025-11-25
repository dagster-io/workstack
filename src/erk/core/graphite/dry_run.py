"""Re-export from erk_shared for backward compatibility."""

from erk_shared.integrations.graphite.dry_run import DryRunGraphite

# Keep old name for compatibility
DryRunGraphiteIntegration = DryRunGraphite

__all__ = ["DryRunGraphite", "DryRunGraphiteIntegration"]
