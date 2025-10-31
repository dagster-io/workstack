"""Bundled kit source resolver."""

from pathlib import Path

from dot_agent_kit.io import load_kit_manifest
from dot_agent_kit.sources.resolver import KitSource, ResolvedKit


class BundledKitSource(KitSource):
    """Resolve kits from bundled package data."""

    def can_resolve(self, source: str) -> bool:
        """Check if source is a bundled kit."""
        bundled_path = self._get_bundled_kit_path(source)
        if bundled_path is None:
            return False
        manifest_path = bundled_path / "kit.yaml"
        return manifest_path.exists()

    def resolve(self, source: str) -> ResolvedKit:
        """Resolve kit from bundled data."""
        bundled_path = self._get_bundled_kit_path(source)
        if bundled_path is None:
            raise ValueError(f"No bundled kit found: {source}")

        manifest_path = bundled_path / "kit.yaml"
        if not manifest_path.exists():
            raise ValueError(f"No kit.yaml found for bundled kit: {source}")

        manifest = load_kit_manifest(manifest_path)

        # Note: Hyphenated naming (e.g., skills/kit-name-tool/) is the standard
        # convention but not enforced by validation

        # Artifacts are relative to manifest location
        artifacts_base = manifest_path.parent

        return ResolvedKit(
            kit_id=manifest.name,
            source_type="bundled",
            source=source,
            manifest_path=manifest_path,
            artifacts_base=artifacts_base,
        )

    def list_available(self) -> list[str]:
        """List all bundled kit IDs."""
        data_dir = Path(__file__).parent.parent / "data" / "kits"
        if not data_dir.exists():
            return []

        bundled_kits = []
        for kit_dir in data_dir.iterdir():
            if kit_dir.is_dir() and (kit_dir / "kit.yaml").exists():
                bundled_kits.append(kit_dir.name)

        return bundled_kits

    def _get_bundled_kit_path(self, source: str) -> Path | None:
        """Get path to bundled kit if it exists."""
        # Path to bundled kits in package data
        data_dir = Path(__file__).parent.parent / "data" / "kits" / source
        if data_dir.exists():
            return data_dir
        return None
