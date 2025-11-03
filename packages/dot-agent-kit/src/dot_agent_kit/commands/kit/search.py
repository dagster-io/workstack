"""Search command for finding kits in the registry."""

import click

from dot_agent_kit.io import load_registry


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
        click.echo("Registry is empty")
        return

    # Filter by query if provided
    if query is not None:
        query_lower = query.lower()
        filtered = [
            entry
            for entry in registry
            if query_lower in entry.name.lower()
            or query_lower in entry.description.lower()
            or query_lower in entry.kit_id.lower()
        ]
    else:
        filtered = registry

    if len(filtered) == 0:
        if query:
            click.echo(f"No kits found matching '{query}'")
        else:
            click.echo("No kits available")
        return

    # Display results
    if query:
        click.echo(f"Found {len(filtered)} kit(s) matching '{query}':\n")
    else:
        click.echo(f"Available kits ({len(filtered)}):\n")

    for entry in filtered:
        click.echo(f"  {entry.name}")
        click.echo(f"  └─ {entry.description}")
        click.echo(f"     Source: {entry.source}")
        click.echo()
