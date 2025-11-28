"""Business logic for session management."""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from erk_bot_server.context import ServerContext
from erk_bot_server.models.session import Session, SessionStatus, StreamEvent, StreamEventType


class SessionNotFoundError(Exception):
    """Raised when a session is not found."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Session {session_id} not found")


class SessionService:
    """Business logic for session management.

    This service orchestrates between the session store and Claude runner,
    implementing retry logic and other business rules.
    """

    def __init__(self, ctx: ServerContext) -> None:
        """Create SessionService with server context.

        Args:
            ctx: Server context with injected dependencies
        """
        self._ctx = ctx

    async def create_session(
        self,
        working_directory: str,
        external_id: str | None = None,
    ) -> Session:
        """Create a new session.

        Args:
            working_directory: Working directory for Claude CLI
            external_id: Optional external identifier (e.g., Slack thread ID)

        Returns:
            Created session
        """
        session = Session(
            session_id=str(uuid.uuid4()),
            external_id=external_id,
            working_directory=working_directory,
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await self._ctx.session_store.create_session(session)
        return session

    async def get_session(self, session_id: str) -> Session:
        """Get a session by ID.

        Args:
            session_id: UUID of the session

        Returns:
            Session

        Raises:
            SessionNotFoundError: If session does not exist
        """
        session = await self._ctx.session_store.get_session(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session

    async def get_session_by_external_id(self, external_id: str) -> Session | None:
        """Get a session by external ID.

        Args:
            external_id: External identifier

        Returns:
            Session if found, None otherwise
        """
        return await self._ctx.session_store.get_session_by_external_id(external_id)

    async def list_sessions(self) -> list[Session]:
        """List all sessions.

        Returns:
            List of sessions ordered by created_at descending
        """
        return await self._ctx.session_store.list_sessions()

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: UUID of the session

        Returns:
            True if deleted, False if not found
        """
        return await self._ctx.session_store.delete_session(session_id)

    async def send_message(
        self,
        session_id: str,
        message: str,
    ) -> AsyncIterator[StreamEvent]:
        """Send a message to a session and stream the response.

        Implements retry-once logic: if Claude CLI fails, retry once
        before returning an error event.

        Args:
            session_id: UUID of the session
            message: User message to send

        Yields:
            StreamEvent objects as they arrive

        Raises:
            SessionNotFoundError: If session does not exist
        """
        session = await self.get_session(session_id)

        # Try up to 2 times (initial + 1 retry)
        for attempt in range(2):
            error_event: StreamEvent | None = None
            events_yielded = False

            async for event in self._ctx.claude_runner.execute_message(
                session_id=session.session_id,
                message=message,
                working_directory=session.working_directory,
            ):
                if event.event_type == StreamEventType.ERROR:
                    error_event = event
                    break
                events_yielded = True
                yield event

            # If we got events without error, we're done
            if events_yielded and error_event is None:
                return

            # If no error, we're done
            if error_event is None:
                return

            # If this was the retry attempt, yield the error
            if attempt == 1:
                yield error_event
                return

            # Otherwise, retry (implicit continue to next iteration)
