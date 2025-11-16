"""Status information collectors."""

from erk.status.collectors.base import StatusCollector
from erk.status.collectors.git import GitStatusCollector

__all__ = [
    "StatusCollector",
    "GitStatusCollector",
]
