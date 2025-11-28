"""Abstract interface for Claude CLI execution."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from erk_bot_server.models.session import StreamEvent


class ClaudeRunner(ABC):
    """Abstract interface for executing Claude CLI commands.

    All implementations must implement this interface for testability.
    """

    @abstractmethod
    def execute_message(
        self,
        session_id: str,
        message: str,
        working_directory: str,
    ) -> AsyncIterator[StreamEvent]:
        """Execute a message in a Claude session and stream events.

        Uses `claude --resume <session_id>` to continue an existing session
        or create a new one if the session_id is new to Claude CLI.

        Args:
            session_id: UUID of the session (used with --resume)
            message: User message to send
            working_directory: Working directory for the Claude CLI

        Yields:
            StreamEvent objects as they arrive from Claude CLI

        Note:
            The implementation should yield events as they arrive, not
            buffer them until completion.
        """
        ...
