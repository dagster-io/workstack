"""Re-export from erk_shared for backward compatibility."""

from erk_shared.integrations.graphite.fake import FakeGraphite

# Keep old name for compatibility
FakeGraphiteIntegration = FakeGraphite

__all__ = ["FakeGraphite", "FakeGraphiteIntegration"]
