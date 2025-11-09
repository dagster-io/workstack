"""Abstraction for parallel task execution with timeout handling.

This module provides an interface for executing tasks in parallel with timeout support,
enabling graceful degradation when tasks exceed their time limits. The abstraction allows
for both production execution using real threads and instant test execution using
pre-configured results.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed

logger = logging.getLogger(__name__)


class ParallelTaskRunner(ABC):
    """Abstract interface for parallel task execution with timeouts.

    Implementations must handle task execution with timeout semantics:
    - Tasks that complete successfully return their result
    - Tasks that timeout return None (graceful degradation)
    - Tasks that raise exceptions return None (error boundary)
    """

    @abstractmethod
    def run_parallel(
        self, tasks: dict[str, Callable[[], object]], timeout_per_task: float
    ) -> dict[str, object | None]:
        """Execute tasks in parallel with timeout handling.

        Args:
            tasks: Dictionary mapping task names to zero-argument callables
            timeout_per_task: Maximum time (seconds) to wait for each task

        Returns:
            Dictionary mapping task names to results (None for timeouts/failures)
        """


class RealParallelTaskRunner(ParallelTaskRunner):
    """Production implementation using ThreadPoolExecutor with actual timeouts.

    Uses Python's concurrent.futures for parallel execution with wall-clock timeouts.
    Tasks that exceed their timeout or raise exceptions gracefully degrade to None.
    """

    def run_parallel(
        self, tasks: dict[str, Callable[[], object]], timeout_per_task: float
    ) -> dict[str, object | None]:
        """Execute tasks in parallel using ThreadPoolExecutor.

        Implementation details:
        - Uses max 5 worker threads
        - Total timeout = timeout_per_task * number of tasks
        - Individual result retrieval timeout = 0.1s (should be immediate)
        - TimeoutError or Exception → None result (graceful degradation)
        """
        results: dict[str, object | None] = {}

        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all tasks
            futures = {}
            for task_name, task_callable in tasks.items():
                future = executor.submit(task_callable)
                futures[future] = task_name

            # Calculate total timeout for all tasks
            total_timeout = timeout_per_task * len(futures) if futures else 1.0

            try:
                for future in as_completed(futures, timeout=total_timeout):
                    task_name = futures[future]
                    try:
                        result = future.result(timeout=0.1)  # Should be immediate once complete
                        results[task_name] = result
                    except TimeoutError:
                        # Error boundary: Task timeouts shouldn't fail entire operation
                        logger.debug(f"Task '{task_name}' timed out after {timeout_per_task}s")
                        results[task_name] = None
                    except Exception as e:
                        # Error boundary: Individual task failures shouldn't fail entire operation
                        # This is an acceptable use of exception handling at error boundaries
                        logger.debug(f"Task '{task_name}' failed: {e}")
                        results[task_name] = None
            except TimeoutError:
                # Some tasks didn't complete in time
                # Mark incomplete tasks as None
                for future, task_name in futures.items():
                    if future.running() or not future.done():
                        logger.debug(f"Task '{task_name}' did not complete in time")
                        results[task_name] = None

        return results
