"""Real time implementation using actual time.sleep()."""

import time

from erk_shared.integrations.time.abc import Time


class RealTime(Time):
    """Production implementation using actual time.sleep()."""

    def sleep(self, seconds: float) -> None:
        """Sleep for specified number of seconds using time.sleep().

        Args:
            seconds: Number of seconds to sleep
        """
        time.sleep(seconds)
