"""Tests for SessionService business logic."""

import pytest
from erk_bot_server.context import ServerContext
from erk_bot_server.integrations.claude_runner.fake import FakeClaudeRunner
from erk_bot_server.integrations.session_store.fake import FakeSessionStore
from erk_bot_server.models.session import StreamEvent, StreamEventType
from erk_bot_server.services.session_service import SessionNotFoundError, SessionService


class TestSessionServiceCreate:
    """Tests for create_session."""

    async def test_create_session_returns_session(
        self,
        session_service: SessionService,
    ) -> None:
        """Creating a session should return the new session."""
        session = await session_service.create_session(
            working_directory="/path/to/repo",
            external_id="slack-123",
        )

        assert session.working_directory == "/path/to/repo"
        assert session.external_id == "slack-123"
        assert session.session_id is not None

    async def test_create_session_stores_in_store(
        self,
        session_service: SessionService,
        fake_session_store: FakeSessionStore,
    ) -> None:
        """Creating a session should store it in the session store."""
        session = await session_service.create_session(
            working_directory="/path/to/repo",
        )

        stored = await fake_session_store.get_session(session.session_id)
        assert stored == session


class TestSessionServiceGet:
    """Tests for get_session."""

    async def test_get_existing_session(
        self,
        session_service: SessionService,
    ) -> None:
        """Getting an existing session should return it."""
        created = await session_service.create_session(
            working_directory="/path/to/repo",
        )

        result = await session_service.get_session(created.session_id)
        assert result == created

    async def test_get_nonexistent_raises_error(
        self,
        session_service: SessionService,
    ) -> None:
        """Getting a nonexistent session should raise SessionNotFoundError."""
        with pytest.raises(SessionNotFoundError):
            await session_service.get_session("nonexistent")


class TestSessionServiceList:
    """Tests for list_sessions."""

    async def test_list_sessions_returns_all(
        self,
        session_service: SessionService,
    ) -> None:
        """Listing sessions should return all sessions."""
        s1 = await session_service.create_session(working_directory="/path1")
        s2 = await session_service.create_session(working_directory="/path2")

        result = await session_service.list_sessions()
        assert len(result) == 2
        assert s1 in result
        assert s2 in result


class TestSessionServiceDelete:
    """Tests for delete_session."""

    async def test_delete_existing_returns_true(
        self,
        session_service: SessionService,
    ) -> None:
        """Deleting an existing session should return True."""
        session = await session_service.create_session(working_directory="/path")

        result = await session_service.delete_session(session.session_id)
        assert result is True

    async def test_delete_nonexistent_returns_false(
        self,
        session_service: SessionService,
    ) -> None:
        """Deleting a nonexistent session should return False."""
        result = await session_service.delete_session("nonexistent")
        assert result is False


class TestSessionServiceSendMessage:
    """Tests for send_message."""

    async def test_send_message_returns_events(
        self,
        session_service: SessionService,
    ) -> None:
        """Sending a message should return stream events."""
        session = await session_service.create_session(working_directory="/path")

        events = []
        async for event in session_service.send_message(session.session_id, "Hello"):
            events.append(event)

        assert len(events) >= 1
        assert events[-1].event_type == StreamEventType.DONE

    async def test_send_message_to_nonexistent_raises(
        self,
        session_service: SessionService,
    ) -> None:
        """Sending to a nonexistent session should raise error."""
        with pytest.raises(SessionNotFoundError):
            async for _ in session_service.send_message("nonexistent", "Hello"):
                pass


class TestSessionServiceRetry:
    """Tests for retry logic."""

    async def test_retry_on_first_failure(self) -> None:
        """Should retry once on failure."""
        # Create a runner that tracks call count
        call_count = 0
        error_event = StreamEvent(
            event_type=StreamEventType.ERROR,
            content="Simulated failure",
        )
        success_events = [
            StreamEvent(event_type=StreamEventType.ASSISTANT_TEXT, content="Success"),
            StreamEvent(event_type=StreamEventType.DONE, content=""),
        ]

        class RetryTestRunner(FakeClaudeRunner):
            async def execute_message(
                self,
                session_id: str,
                message: str,
                working_directory: str,
            ):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    yield error_event
                else:
                    for event in success_events:
                        yield event

        ctx = ServerContext(
            session_store=FakeSessionStore(),
            claude_runner=RetryTestRunner(),
        )
        service = SessionService(ctx)

        session = await service.create_session(working_directory="/path")

        events = []
        async for event in service.send_message(session.session_id, "Hello"):
            events.append(event)

        assert call_count == 2
        assert events[0].content == "Success"
        assert events[1].event_type == StreamEventType.DONE

    async def test_return_error_after_retry(self) -> None:
        """Should return error event after retry fails."""
        ctx = ServerContext(
            session_store=FakeSessionStore(),
            claude_runner=FakeClaudeRunner(
                should_fail=True,
                failure_message="Persistent failure",
            ),
        )
        service = SessionService(ctx)

        session = await service.create_session(working_directory="/path")

        events = []
        async for event in service.send_message(session.session_id, "Hello"):
            events.append(event)

        assert len(events) == 1
        assert events[0].event_type == StreamEventType.ERROR
        assert events[0].content == "Persistent failure"
