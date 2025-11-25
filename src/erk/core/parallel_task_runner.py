"""Re-export from erk_shared for backward compatibility."""

from erk_shared.integrations.parallel import ParallelTaskRunner, RealParallelTaskRunner

__all__ = ["ParallelTaskRunner", "RealParallelTaskRunner"]
