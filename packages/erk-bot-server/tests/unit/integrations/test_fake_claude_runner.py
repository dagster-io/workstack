"""Tests for FakeClaudeRunner implementation."""

from erk_bot_server.integrations.claude_runner.fake import FakeClaudeRunner
from erk_bot_server.models.session import StreamEvent, StreamEventType


class TestFakeClaudeRunnerExecute:
    """Tests for execute_message."""

    async def test_execute_tracks_message(
        self,
        fake_claude_runner: FakeClaudeRunner,
    ) -> None:
        """Executing a message should track the call."""
        events = []
        async for event in fake_claude_runner.execute_message(
            session_id="test-session",
            message="Hello",
            working_directory="/path",
        ):
            events.append(event)

        assert fake_claude_runner.executed_messages == [("test-session", "Hello", "/path")]

    async def test_execute_returns_default_response(
        self,
        fake_claude_runner: FakeClaudeRunner,
    ) -> None:
        """Executing should return default response when no configured response."""
        events = []
        async for event in fake_claude_runner.execute_message(
            session_id="test-session",
            message="Hello",
            working_directory="/path",
        ):
            events.append(event)

        assert len(events) == 2
        assert events[0].event_type == StreamEventType.ASSISTANT_TEXT
        assert "fake Claude response" in events[0].content
        assert events[1].event_type == StreamEventType.DONE

    async def test_execute_returns_configured_response(self) -> None:
        """Executing should return configured response for session."""
        custom_events = [
            StreamEvent(
                event_type=StreamEventType.ASSISTANT_TEXT,
                content="Custom response",
            ),
            StreamEvent(
                event_type=StreamEventType.DONE,
                content="",
            ),
        ]
        runner = FakeClaudeRunner(responses={"test-session": custom_events})

        events = []
        async for event in runner.execute_message(
            session_id="test-session",
            message="Hello",
            working_directory="/path",
        ):
            events.append(event)

        assert len(events) == 2
        assert events[0].content == "Custom response"


class TestFakeClaudeRunnerFailure:
    """Tests for failure simulation."""

    async def test_should_fail_returns_error(self) -> None:
        """When should_fail=True, should return error event."""
        runner = FakeClaudeRunner(should_fail=True, failure_message="Test failure")

        events = []
        async for event in runner.execute_message(
            session_id="test-session",
            message="Hello",
            working_directory="/path",
        ):
            events.append(event)

        assert len(events) == 1
        assert events[0].event_type == StreamEventType.ERROR
        assert events[0].content == "Test failure"
