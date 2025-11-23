"""Time operations abstraction for testing.

This module provides an ABC for time operations (sleep, etc.) to enable
fast tests that don't actually sleep. Future extensions may include
datetime.now() and other clock-related operations.
"""

import time
from abc import ABC, abstractmethod


class Time(ABC):
    """Abstract time operations for dependency injection."""

    @abstractmethod
    def sleep(self, seconds: float) -> None:
        """Sleep for specified number of seconds.

        Args:
            seconds: Number of seconds to sleep
        """
        ...


class RealTime(Time):
    """Production implementation using actual time.sleep()."""

    def sleep(self, seconds: float) -> None:
        """Sleep for specified number of seconds using time.sleep().

        Args:
            seconds: Number of seconds to sleep
        """
        time.sleep(seconds)
