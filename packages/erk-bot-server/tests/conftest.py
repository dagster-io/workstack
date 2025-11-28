"""Pytest configuration and fixtures."""

from collections.abc import AsyncGenerator

import pytest
from erk_bot_server.context import ServerContext
from erk_bot_server.integrations.claude_runner.fake import FakeClaudeRunner
from erk_bot_server.integrations.session_store.fake import FakeSessionStore
from erk_bot_server.main import create_app
from erk_bot_server.services.session_service import SessionService
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def fake_session_store() -> FakeSessionStore:
    """Create a fresh FakeSessionStore."""
    return FakeSessionStore()


@pytest.fixture
def fake_claude_runner() -> FakeClaudeRunner:
    """Create a fresh FakeClaudeRunner."""
    return FakeClaudeRunner()


@pytest.fixture
def server_context(
    fake_session_store: FakeSessionStore,
    fake_claude_runner: FakeClaudeRunner,
) -> ServerContext:
    """Create a ServerContext with fake implementations."""
    return ServerContext(
        session_store=fake_session_store,
        claude_runner=fake_claude_runner,
    )


@pytest.fixture
def session_service(server_context: ServerContext) -> SessionService:
    """Create a SessionService with fake context."""
    return SessionService(server_context)


@pytest.fixture
async def async_client(
    fake_session_store: FakeSessionStore,
    fake_claude_runner: FakeClaudeRunner,
) -> AsyncGenerator[AsyncClient]:
    """Create an async test client."""
    app = create_app()

    # Override the session service with our fakes
    ctx = ServerContext(
        session_store=fake_session_store,
        claude_runner=fake_claude_runner,
    )
    app.state.session_service = SessionService(ctx)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
