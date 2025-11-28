"""In-memory fake implementation of ClaudeRunner for testing."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime

from erk_bot_server.integrations.claude_runner.abc import ClaudeRunner
from erk_bot_server.models.session import StreamEvent, StreamEventType


class FakeClaudeRunner(ClaudeRunner):
    """In-memory fake implementation for testing.

    All state is provided via constructor using keyword arguments.
    This class has NO public setup methods.
    """

    def __init__(
        self,
        *,
        responses: dict[str, list[StreamEvent]] | None = None,
        default_response: list[StreamEvent] | None = None,
        should_fail: bool = False,
        failure_message: str = "Simulated CLI failure",
    ) -> None:
        """Create FakeClaudeRunner with pre-configured responses.

        Args:
            responses: Mapping of session_id -> list of StreamEvents to return
            default_response: Events to return when session_id not in responses
            should_fail: If True, always yield an error event
            failure_message: Message for error events when should_fail=True
        """
        self._responses = responses or {}
        self._default_response = default_response or [
            StreamEvent(
                event_type=StreamEventType.ASSISTANT_TEXT,
                content="Hello! I'm a fake Claude response.",
            ),
            StreamEvent(
                event_type=StreamEventType.DONE,
                content="",
            ),
        ]
        self._should_fail = should_fail
        self._failure_message = failure_message
        self._executed_messages: list[tuple[str, str, str]] = []

    @property
    def executed_messages(self) -> list[tuple[str, str, str]]:
        """Read-only access to executed messages for test assertions.

        Returns list of (session_id, message, working_directory) tuples.
        """
        return self._executed_messages.copy()

    async def execute_message(
        self,
        session_id: str,
        message: str,
        working_directory: str,
    ) -> AsyncIterator[StreamEvent]:
        """Yield pre-configured events from fake storage."""
        self._executed_messages.append((session_id, message, working_directory))

        if self._should_fail:
            yield StreamEvent(
                event_type=StreamEventType.ERROR,
                content=self._failure_message,
                timestamp=datetime.now(UTC),
            )
            return

        events = self._responses.get(session_id, self._default_response)
        for event in events:
            yield event
