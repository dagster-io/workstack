"""Re-export from erk_shared for backward compatibility."""

from erk_shared.printing.base import PrintingBase

# Keep old name for compatibility
PrintingIntegration = PrintingBase

__all__ = ["PrintingBase", "PrintingIntegration"]
