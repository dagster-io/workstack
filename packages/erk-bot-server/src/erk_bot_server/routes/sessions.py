"""HTTP route handlers for session management."""

from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from erk_bot_server.models.session import Session, StreamEventType
from erk_bot_server.services.session_service import SessionNotFoundError, SessionService

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    """Request body for creating a session."""

    working_directory: str
    external_id: str | None = None


class CreateSessionResponse(BaseModel):
    """Response body for session creation."""

    session_id: str
    external_id: str | None
    status: str


class SessionResponse(BaseModel):
    """Response body for session info."""

    session_id: str
    external_id: str | None
    working_directory: str
    status: str
    created_at: str
    updated_at: str

    @classmethod
    def from_session(cls, session: Session) -> "SessionResponse":
        """Create response from Session model."""
        return cls(
            session_id=session.session_id,
            external_id=session.external_id,
            working_directory=session.working_directory,
            status=session.status.value,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
        )


class SendMessageRequest(BaseModel):
    """Request body for sending a message."""

    message: str


def get_session_service(request: Request) -> SessionService:
    """Get SessionService from request state."""
    return request.app.state.session_service


@router.post("", response_model=CreateSessionResponse)
async def create_session(
    request: Request,
    body: CreateSessionRequest,
) -> CreateSessionResponse:
    """Create a new session."""
    service = get_session_service(request)
    session = await service.create_session(
        working_directory=body.working_directory,
        external_id=body.external_id,
    )
    return CreateSessionResponse(
        session_id=session.session_id,
        external_id=session.external_id,
        status=session.status.value,
    )


@router.get("", response_model=list[SessionResponse])
async def list_sessions(request: Request) -> list[SessionResponse]:
    """List all sessions."""
    service = get_session_service(request)
    sessions = await service.list_sessions()
    return [SessionResponse.from_session(s) for s in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(request: Request, session_id: str) -> SessionResponse:
    """Get a session by ID."""
    service = get_session_service(request)
    try:
        session = await service.get_session(session_id)
        return SessionResponse.from_session(session)
    except SessionNotFoundError as err:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found") from err


@router.delete("/{session_id}")
async def delete_session(request: Request, session_id: str) -> dict[str, bool]:
    """Delete a session."""
    service = get_session_service(request)
    deleted = await service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return {"deleted": True}


@router.post("/{session_id}/messages")
async def send_message(
    request: Request,
    session_id: str,
    body: SendMessageRequest,
) -> StreamingResponse:
    """Send a message and stream the response via SSE."""
    service = get_session_service(request)

    # Verify session exists before streaming
    try:
        await service.get_session(session_id)
    except SessionNotFoundError as err:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found") from err

    async def event_generator() -> AsyncGenerator[str]:
        """Generate SSE events from Claude response."""
        async for event in service.send_message(session_id, body.message):
            event_type = event.event_type.value
            content = event.content.replace("\n", "\\n")  # Escape newlines for SSE
            yield f"event: {event_type}\ndata: {content}\n\n"

            # If we got a done or error event, stop
            if event.event_type in (StreamEventType.DONE, StreamEventType.ERROR):
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
