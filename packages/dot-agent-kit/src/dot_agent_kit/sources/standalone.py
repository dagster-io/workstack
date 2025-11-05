"""Standalone package source resolver."""

from dot_agent_kit.io import load_kit_manifest
from dot_agent_kit.sources.exceptions import (
    KitManifestError,
    KitNotFoundError,
    SourceAccessError,
    SourceFormatError,
)
from dot_agent_kit.sources.resolver import KitSource, ResolvedKit, parse_source
from dot_agent_kit.utils import find_kit_manifest, get_package_path, is_package_installed


class StandalonePackageSource(KitSource):
    """Resolve kits from standalone Python packages."""

    def can_resolve(self, source: str) -> bool:
        """Check if source is an installed Python package."""
        # Must have "package:" prefix
        if ":" not in source:
            return False

        prefix, identifier = parse_source(source)
        if prefix != "package":
            return False

        return is_package_installed(identifier)

    def resolve(self, source: str) -> ResolvedKit:
        """Resolve kit from Python package."""
        prefix, identifier = parse_source(source)
        if prefix != "package":
            raise SourceFormatError(source, "StandalonePackageSource requires 'package:' prefix")

        if not is_package_installed(identifier):
            raise KitNotFoundError(identifier, ["package"])

        package_path = get_package_path(identifier)
        if package_path is None:
            raise SourceAccessError("package", identifier)

        manifest_path = find_kit_manifest(package_path)
        if manifest_path is None:
            raise KitManifestError(package_path / "kit.yaml")

        manifest = load_kit_manifest(manifest_path)

        # Artifacts are relative to manifest location
        artifacts_base = manifest_path.parent

        return ResolvedKit(
            kit_id=manifest.name,
            version=manifest.version,
            source_type="package",
            source=source,
            manifest_path=manifest_path,
            artifacts_base=artifacts_base,
        )

    def list_available(self) -> list[str]:
        """List available kits from standalone packages.

        For standalone packages, we cannot enumerate all installed packages
        that might be kits, so we return an empty list. Users must explicitly
        specify package names to install.
        """
        return []
