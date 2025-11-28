"""Session and streaming event data models."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class SessionStatus(str, Enum):
    """Status of a Claude session."""

    ACTIVE = "active"


class StreamEventType(str, Enum):
    """Types of streaming events from Claude CLI."""

    ASSISTANT_TEXT = "assistant_text"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    DONE = "done"


@dataclass(frozen=True)
class Session:
    """A Claude CLI session.

    Sessions are identified by session_id (UUID) and can optionally have
    an external_id for mapping to external systems like Slack threads.
    """

    session_id: str
    external_id: str | None
    working_directory: str
    status: SessionStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class StreamEvent:
    """A single streaming event from Claude CLI.

    Events are emitted during message processing and include assistant
    text chunks, tool usage, and completion/error signals.
    """

    event_type: StreamEventType
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
