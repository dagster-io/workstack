"""Data models for command execution."""

from dataclasses import dataclass
from typing import Any

from claude_agent_sdk import ResultMessage


@dataclass(frozen=True)
class CommandResult:
    """Result of command execution."""

    sdk_result: ResultMessage
    data: dict[str, Any]


class CommandNotFoundError(Exception):
    """Raised when command file not found."""

    pass
