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
        yaml_manifest = bundled_path / "kit.yaml"
        toml_manifest = bundled_path / "kit.toml"
        return yaml_manifest.exists() or toml_manifest.exists()

    def resolve(self, source: str) -> ResolvedKit:
        """Resolve kit from bundled data."""
        bundled_path = self._get_bundled_kit_path(source)
        if bundled_path is None:
            raise ValueError(f"No bundled kit found: {source}")

        # Try both kit.toml and kit.yaml
        toml_manifest = bundled_path / "kit.toml"
        yaml_manifest = bundled_path / "kit.yaml"

        if toml_manifest.exists():
            manifest_path = toml_manifest
        elif yaml_manifest.exists():
            manifest_path = yaml_manifest
        else:
            raise ValueError(f"No kit manifest found for bundled kit: {source}")

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
            if kit_dir.is_dir():
                # Check for either kit.yaml or kit.toml
                has_yaml = (kit_dir / "kit.yaml").exists()
                has_toml = (kit_dir / "kit.toml").exists()
                if has_yaml or has_toml:
                    bundled_kits.append(kit_dir.name)

        return bundled_kits

    def _get_bundled_kit_path(self, source: str) -> Path | None:
        """Get path to bundled kit if it exists."""
        # Path to bundled kits in package data
        data_dir = Path(__file__).parent.parent / "data" / "kits" / source
        if data_dir.exists():
            return data_dir
        return None
