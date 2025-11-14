"""Search command for finding kits in the registry."""

import click

from dot_agent_kit.cli.output import user_output
from dot_agent_kit.io import load_kit_manifest, load_registry
from dot_agent_kit.models.types import SOURCE_TYPE_BUNDLED
from dot_agent_kit.sources.bundled import BundledKitSource


@click.command()
@click.argument("query", required=False)
def search(query: str | None) -> None:
    """Search for kits or list all available bundled kits.

    When no query is provided, lists all available kits.
    When a query is provided, searches kit names, descriptions, and IDs.

    Examples:
        # List all available bundled kits
        dot-agent kit search

        # Search for specific kits
        dot-agent kit search github

        # Search by description
        dot-agent kit search "workflow"
    """
    registry = load_registry()

    if len(registry) == 0:
        user_output("Registry is empty")
        return

    # Filter by query if provided
    if query is not None:
        query_lower = query.lower()
        filtered = [
            entry
            for entry in registry
            if query_lower in entry.kit_id.lower() or query_lower in entry.description.lower()
        ]
    else:
        filtered = registry

    if len(filtered) == 0:
        if query:
            user_output(f"No kits found matching '{query}'")
        else:
            user_output("No kits available")
        return

    # Display results
    if query:
        user_output(f"Found {len(filtered)} kit(s) matching '{query}':\n")
    else:
        user_output(f"Available kits ({len(filtered)}):\n")

    bundled_source = BundledKitSource()

    for entry in filtered:
        # Load manifest to get version and artifact counts
        version_str = ""
        artifacts_str = ""

        if entry.source_type == SOURCE_TYPE_BUNDLED and bundled_source.can_resolve(entry.kit_id):
            resolved = bundled_source.resolve(entry.kit_id)
            manifest = load_kit_manifest(resolved.manifest_path)

            version_str = f" (v{manifest.version})"

            # Count artifacts by type
            artifact_counts = []
            for artifact_type, paths in manifest.artifacts.items():
                count = len(paths)
                if count > 0:
                    # Use singular or plural form based on count
                    type_name = artifact_type
                    if count == 1:
                        # Singularize: remove trailing 's' if present
                        if type_name.endswith("s"):
                            type_name = type_name[:-1]
                    else:
                        # Pluralize: add 's' if not already present
                        if not type_name.endswith("s"):
                            type_name = type_name + "s"
                    artifact_counts.append(f"{count} {type_name}")

            if artifact_counts:
                artifacts_str = f" • {', '.join(artifact_counts)}"

        user_output(f"  [{entry.kit_id}]{version_str}")
        user_output(f"  └─ {entry.description}{artifacts_str}")
        user_output()
