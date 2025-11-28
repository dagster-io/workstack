"""FastAPI application for erk bot server."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from erk_bot_server.config import Settings
from erk_bot_server.context import ServerContext
from erk_bot_server.integrations.claude_runner.fake import FakeClaudeRunner
from erk_bot_server.integrations.session_store.fake import FakeSessionStore
from erk_bot_server.routes import sessions
from erk_bot_server.services.session_service import SessionService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan context manager.

    Sets up dependencies on startup and cleans up on shutdown.
    """
    # For MVP, use fake implementations
    # TODO: Add Redis and real Claude runner implementations
    ctx = ServerContext(
        session_store=FakeSessionStore(),
        claude_runner=FakeClaudeRunner(),
    )

    # Create session service and attach to app state
    app.state.session_service = SessionService(ctx)

    yield

    # Cleanup (none needed for fake implementations)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional settings override for testing

    Returns:
        Configured FastAPI application
    """
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="Erk Bot Server",
        description="API for managing Claude CLI sessions",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(sessions.router)

    return app


# Default app instance for uvicorn
app = create_app()
