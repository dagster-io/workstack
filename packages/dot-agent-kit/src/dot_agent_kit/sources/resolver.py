"""Kit source resolution system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from dot_agent_kit.sources.exceptions import ResolverNotConfiguredError


@dataclass(frozen=True)
class ResolvedKit:
    """A kit resolved from a source."""

    kit_id: str
    version: str
    source_type: str
    source: str
    manifest_path: Path
    artifacts_base: Path


class KitSource(ABC):
    """Abstract base class for kit sources."""

    @abstractmethod
    def can_resolve(self, source: str) -> bool:
        """Check if this source can resolve the given identifier."""
        pass

    @abstractmethod
    def resolve(self, source: str) -> ResolvedKit:
        """Resolve a kit from the source."""
        pass

    @abstractmethod
    def list_available(self) -> list[str]:
        """List all kit IDs available from this source."""
        pass


class KitResolver:
    """Multi-source kit resolver."""

    def __init__(self, sources: list[KitSource]) -> None:
        self.sources = sources

    def resolve(self, source: str) -> ResolvedKit:
        """Resolve a kit from any available source.

        Raises:
            ResolverNotConfiguredError: If no resolver can handle the source
            KitNotFoundError: If kit not found (should be raised by sources)
            SourceAccessError: If source cannot be accessed (should be raised by sources)
        """
        for resolver_source in self.sources:
            if resolver_source.can_resolve(source):
                return resolver_source.resolve(source)

        # No resolver found - provide detailed error
        available_types = [type(source).__name__ for source in self.sources]
        raise ResolverNotConfiguredError(source, available_types)
