"""Search command for finding kits."""

import click

from dot_agent_kit.io import load_registry


@click.command()
@click.argument("query", required=False)
def search(query: str | None) -> None:
    """Search for kits in the registry."""
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
        click.echo(f"No kits found matching '{query}'")
        return

    # Display results
    click.echo(f"Found {len(filtered)} kit(s):\n")

    for entry in filtered:
        click.echo(f"  {entry.name}")
        click.echo(f"  └─ {entry.description}")
        click.echo(f"     Source: {entry.source}")
        click.echo()
