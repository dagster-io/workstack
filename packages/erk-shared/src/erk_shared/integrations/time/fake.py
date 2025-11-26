"""Fake Time implementation for testing.

FakeTime is an in-memory implementation that tracks sleep() calls without
actually sleeping, enabling fast tests.
"""

from erk_shared.integrations.time.abc import Time


class FakeTime(Time):
    """In-memory fake implementation that tracks calls without sleeping.

    This class has NO public setup methods. All state is provided via constructor
    or captured during execution.
    """

    def __init__(self) -> None:
        """Create FakeTime with empty call tracking."""
        self._sleep_calls: list[float] = []

    @property
    def sleep_calls(self) -> list[float]:
        """Get the list of sleep() calls that were made.

        Returns list of seconds values passed to sleep().

        This property is for test assertions only.
        """
        return self._sleep_calls

    def sleep(self, seconds: float) -> None:
        """Track sleep call without actually sleeping.

        Args:
            seconds: Number of seconds that would have been slept
        """
        self._sleep_calls.append(seconds)
