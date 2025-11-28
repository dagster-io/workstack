"""Abstract interface for session storage."""

from abc import ABC, abstractmethod

from erk_bot_server.models.session import Session


class SessionStore(ABC):
    """Abstract interface for session storage.

    All implementations (Redis, in-memory fake) must implement this interface.
    All methods are async to support Redis operations.
    """

    @abstractmethod
    async def create_session(self, session: Session) -> None:
        """Store a new session.

        Args:
            session: Session to create

        Raises:
            ValueError: If session_id already exists
        """
        ...

    @abstractmethod
    async def get_session(self, session_id: str) -> Session | None:
        """Retrieve a session by ID.

        Args:
            session_id: UUID of the session

        Returns:
            Session if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_session_by_external_id(self, external_id: str) -> Session | None:
        """Retrieve a session by external ID.

        Args:
            external_id: External identifier (e.g., Slack thread ID)

        Returns:
            Session if found, None otherwise
        """
        ...

    @abstractmethod
    async def list_sessions(self) -> list[Session]:
        """List all sessions.

        Returns:
            List of all sessions, ordered by created_at descending
        """
        ...

    @abstractmethod
    async def update_session(self, session: Session) -> None:
        """Update an existing session.

        Args:
            session: Session with updated fields

        Raises:
            KeyError: If session_id does not exist
        """
        ...

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID.

        Args:
            session_id: UUID of the session to delete

        Returns:
            True if session was deleted, False if not found
        """
        ...

    @abstractmethod
    async def session_exists(self, session_id: str) -> bool:
        """Check if a session exists.

        Args:
            session_id: UUID of the session

        Returns:
            True if session exists, False otherwise
        """
        ...
