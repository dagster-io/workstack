"""Tests for FakeSessionStore implementation."""

from datetime import UTC, datetime

import pytest
from erk_bot_server.integrations.session_store.fake import FakeSessionStore
from erk_bot_server.models.session import Session, SessionStatus


@pytest.fixture
def sample_session() -> Session:
    """Create a sample session for testing."""
    return Session(
        session_id="test-session-id",
        external_id="slack-thread-123",
        working_directory="/path/to/repo",
        status=SessionStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestFakeSessionStoreCreate:
    """Tests for create_session."""

    async def test_create_session_stores_session(
        self,
        fake_session_store: FakeSessionStore,
        sample_session: Session,
    ) -> None:
        """Creating a session should store it."""
        await fake_session_store.create_session(sample_session)

        result = await fake_session_store.get_session(sample_session.session_id)
        assert result == sample_session

    async def test_create_session_tracks_mutation(
        self,
        fake_session_store: FakeSessionStore,
        sample_session: Session,
    ) -> None:
        """Creating a session should track the mutation."""
        await fake_session_store.create_session(sample_session)

        assert sample_session in fake_session_store.created_sessions

    async def test_create_session_maps_external_id(
        self,
        fake_session_store: FakeSessionStore,
        sample_session: Session,
    ) -> None:
        """Creating a session should map external_id to session_id."""
        await fake_session_store.create_session(sample_session)

        result = await fake_session_store.get_session_by_external_id("slack-thread-123")
        assert result == sample_session

    async def test_create_duplicate_raises_error(
        self,
        fake_session_store: FakeSessionStore,
        sample_session: Session,
    ) -> None:
        """Creating a duplicate session should raise ValueError."""
        await fake_session_store.create_session(sample_session)

        with pytest.raises(ValueError, match="already exists"):
            await fake_session_store.create_session(sample_session)


class TestFakeSessionStoreGet:
    """Tests for get_session."""

    async def test_get_nonexistent_returns_none(
        self,
        fake_session_store: FakeSessionStore,
    ) -> None:
        """Getting a nonexistent session should return None."""
        result = await fake_session_store.get_session("nonexistent")
        assert result is None


class TestFakeSessionStoreList:
    """Tests for list_sessions."""

    async def test_list_empty_returns_empty(
        self,
        fake_session_store: FakeSessionStore,
    ) -> None:
        """Listing sessions when empty should return empty list."""
        result = await fake_session_store.list_sessions()
        assert result == []

    async def test_list_returns_sessions_descending(
        self,
        fake_session_store: FakeSessionStore,
    ) -> None:
        """Listing sessions should return them in descending created_at order."""
        older = Session(
            session_id="older",
            external_id=None,
            working_directory="/path",
            status=SessionStatus.ACTIVE,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        newer = Session(
            session_id="newer",
            external_id=None,
            working_directory="/path",
            status=SessionStatus.ACTIVE,
            created_at=datetime(2024, 6, 1, tzinfo=UTC),
            updated_at=datetime(2024, 6, 1, tzinfo=UTC),
        )

        await fake_session_store.create_session(older)
        await fake_session_store.create_session(newer)

        result = await fake_session_store.list_sessions()
        assert result == [newer, older]


class TestFakeSessionStoreDelete:
    """Tests for delete_session."""

    async def test_delete_existing_returns_true(
        self,
        fake_session_store: FakeSessionStore,
        sample_session: Session,
    ) -> None:
        """Deleting an existing session should return True."""
        await fake_session_store.create_session(sample_session)

        result = await fake_session_store.delete_session(sample_session.session_id)
        assert result is True

    async def test_delete_removes_session(
        self,
        fake_session_store: FakeSessionStore,
        sample_session: Session,
    ) -> None:
        """Deleting should remove the session."""
        await fake_session_store.create_session(sample_session)
        await fake_session_store.delete_session(sample_session.session_id)

        result = await fake_session_store.get_session(sample_session.session_id)
        assert result is None

    async def test_delete_removes_external_id_mapping(
        self,
        fake_session_store: FakeSessionStore,
        sample_session: Session,
    ) -> None:
        """Deleting should remove the external_id mapping."""
        await fake_session_store.create_session(sample_session)
        await fake_session_store.delete_session(sample_session.session_id)

        result = await fake_session_store.get_session_by_external_id("slack-thread-123")
        assert result is None

    async def test_delete_tracks_mutation(
        self,
        fake_session_store: FakeSessionStore,
        sample_session: Session,
    ) -> None:
        """Deleting should track the mutation."""
        await fake_session_store.create_session(sample_session)
        await fake_session_store.delete_session(sample_session.session_id)

        assert sample_session.session_id in fake_session_store.deleted_session_ids

    async def test_delete_nonexistent_returns_false(
        self,
        fake_session_store: FakeSessionStore,
    ) -> None:
        """Deleting a nonexistent session should return False."""
        result = await fake_session_store.delete_session("nonexistent")
        assert result is False


class TestFakeSessionStoreExists:
    """Tests for session_exists."""

    async def test_exists_true_when_exists(
        self,
        fake_session_store: FakeSessionStore,
        sample_session: Session,
    ) -> None:
        """session_exists should return True when session exists."""
        await fake_session_store.create_session(sample_session)

        result = await fake_session_store.session_exists(sample_session.session_id)
        assert result is True

    async def test_exists_false_when_missing(
        self,
        fake_session_store: FakeSessionStore,
    ) -> None:
        """session_exists should return False when session is missing."""
        result = await fake_session_store.session_exists("nonexistent")
        assert result is False
