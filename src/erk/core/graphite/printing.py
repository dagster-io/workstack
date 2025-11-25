"""Re-export from erk_shared for backward compatibility."""

from erk_shared.integrations.graphite.printing import PrintingGraphite

# Keep old name for compatibility
StackPrinter = PrintingGraphite

__all__ = ["PrintingGraphite", "StackPrinter"]
