"""Server context for dependency injection."""

from dataclasses import dataclass

from erk_bot_server.integrations.claude_runner.abc import ClaudeRunner
from erk_bot_server.integrations.claude_runner.fake import FakeClaudeRunner
from erk_bot_server.integrations.session_store.abc import SessionStore
from erk_bot_server.integrations.session_store.fake import FakeSessionStore
from erk_bot_server.models.session import Session, StreamEvent


@dataclass(frozen=True)
class ServerContext:
    """Server context containing all dependencies.

    This is a frozen dataclass that holds all injected dependencies
    for the server. Use for_test() for testing scenarios.
    """

    session_store: SessionStore
    claude_runner: ClaudeRunner

    @classmethod
    def for_test(
        cls,
        *,
        sessions: dict[str, Session] | None = None,
        responses: dict[str, list[StreamEvent]] | None = None,
        should_fail: bool = False,
    ) -> "ServerContext":
        """Create a test context with fake implementations.

        Args:
            sessions: Pre-populated sessions for FakeSessionStore
            responses: Pre-configured responses for FakeClaudeRunner
            should_fail: If True, ClaudeRunner will always fail

        Returns:
            ServerContext with fake implementations
        """
        return cls(
            session_store=FakeSessionStore(sessions=sessions),
            claude_runner=FakeClaudeRunner(
                responses=responses,
                should_fail=should_fail,
            ),
        )
