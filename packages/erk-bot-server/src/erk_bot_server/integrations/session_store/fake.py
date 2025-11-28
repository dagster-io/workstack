"""In-memory fake implementation of SessionStore for testing."""

from erk_bot_server.integrations.session_store.abc import SessionStore
from erk_bot_server.models.session import Session


class FakeSessionStore(SessionStore):
    """In-memory fake implementation for testing.

    All state is provided via constructor using keyword arguments.
    This class has NO public setup methods. All state is provided via
    constructor using keyword arguments with sensible defaults.
    """

    def __init__(
        self,
        *,
        sessions: dict[str, Session] | None = None,
        external_id_map: dict[str, str] | None = None,
    ) -> None:
        """Create FakeSessionStore with pre-configured state.

        Args:
            sessions: Mapping of session_id -> Session
            external_id_map: Mapping of external_id -> session_id
        """
        self._sessions = sessions.copy() if sessions else {}
        self._external_id_map = external_id_map.copy() if external_id_map else {}
        self._created_sessions: list[Session] = []
        self._deleted_session_ids: list[str] = []

    @property
    def created_sessions(self) -> list[Session]:
        """Read-only access to created sessions for test assertions."""
        return self._created_sessions.copy()

    @property
    def deleted_session_ids(self) -> list[str]:
        """Read-only access to deleted session IDs for test assertions."""
        return self._deleted_session_ids.copy()

    @property
    def sessions(self) -> dict[str, Session]:
        """Read-only access to current sessions."""
        return self._sessions.copy()

    async def create_session(self, session: Session) -> None:
        """Store session in fake storage and track mutation."""
        if session.session_id in self._sessions:
            msg = f"Session {session.session_id} already exists"
            raise ValueError(msg)

        self._sessions[session.session_id] = session
        if session.external_id:
            self._external_id_map[session.external_id] = session.session_id
        self._created_sessions.append(session)

    async def get_session(self, session_id: str) -> Session | None:
        """Get session from fake storage."""
        if session_id not in self._sessions:
            return None
        return self._sessions[session_id]

    async def get_session_by_external_id(self, external_id: str) -> Session | None:
        """Get session by external ID from fake storage."""
        if external_id not in self._external_id_map:
            return None
        session_id = self._external_id_map[external_id]
        return await self.get_session(session_id)

    async def list_sessions(self) -> list[Session]:
        """List all sessions, ordered by created_at descending."""
        sessions = list(self._sessions.values())
        return sorted(sessions, key=lambda s: s.created_at, reverse=True)

    async def update_session(self, session: Session) -> None:
        """Update session in fake storage."""
        if session.session_id not in self._sessions:
            msg = f"Session {session.session_id} not found"
            raise KeyError(msg)

        old_session = self._sessions[session.session_id]

        # Update external_id mapping if it changed
        if old_session.external_id and old_session.external_id != session.external_id:
            del self._external_id_map[old_session.external_id]
        if session.external_id:
            self._external_id_map[session.external_id] = session.session_id

        self._sessions[session.session_id] = session

    async def delete_session(self, session_id: str) -> bool:
        """Delete session from fake storage."""
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]
        if session.external_id:
            del self._external_id_map[session.external_id]
        del self._sessions[session_id]
        self._deleted_session_ids.append(session_id)
        return True

    async def session_exists(self, session_id: str) -> bool:
        """Check if session exists in fake storage."""
        return session_id in self._sessions
