"""Kit source resolution system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ResolvedKit:
    """A kit resolved from a source."""

    kit_id: str
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
        """Resolve a kit from any available source."""
        for resolver_source in self.sources:
            if resolver_source.can_resolve(source):
                return resolver_source.resolve(source)

        raise ValueError(f"No resolver found for: {source}")
