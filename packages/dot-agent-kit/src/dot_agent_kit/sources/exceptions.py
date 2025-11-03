"""Custom exceptions for kit resolution errors."""

from pathlib import Path


class KitResolutionError(Exception):
    """Base exception for kit resolution errors."""

    pass


class KitNotFoundError(KitResolutionError):
    """Kit does not exist in any configured source."""

    def __init__(self, kit_id: str, sources_checked: list[str]) -> None:
        self.kit_id = kit_id
        self.sources_checked = sources_checked
        super().__init__(
            f"Kit '{kit_id}' not found in any source. "
            f"Sources checked: {', '.join(sources_checked)}"
        )


class ResolverNotConfiguredError(KitResolutionError):
    """No resolver is configured to handle this source type."""

    def __init__(self, source: str, available_types: list[str]) -> None:
        self.source = source
        self.available_types = available_types
        super().__init__(
            f"No resolver configured for source '{source}'. "
            f"Available resolvers: {', '.join(available_types) if available_types else 'none'}"
        )


class SourceAccessError(KitResolutionError):
    """Failed to access kit source (network, filesystem, etc.)."""

    def __init__(self, source_type: str, source: str, cause: Exception | None = None) -> None:
        self.source_type = source_type
        self.source = source
        self.cause = cause
        message = f"Failed to access {source_type} source '{source}'"
        if cause:
            message += f": {str(cause)}"
        super().__init__(message)


class KitManifestError(KitResolutionError):
    """Error loading or parsing kit manifest."""

    def __init__(self, manifest_path: Path, cause: Exception | None = None) -> None:
        self.manifest_path = manifest_path
        self.cause = cause
        message = f"Failed to load kit manifest from '{manifest_path}'"
        if cause:
            message += f": {str(cause)}"
        super().__init__(message)


class KitVersionError(KitResolutionError):
    """Kit version-related error (version mismatch, invalid version, etc.)."""

    def __init__(self, kit_id: str, message: str) -> None:
        self.kit_id = kit_id
        super().__init__(f"Version error for kit '{kit_id}': {message}")