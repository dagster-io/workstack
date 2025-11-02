"""Check command for validating artifacts."""

from pathlib import Path

import click

from dot_agent_kit.operations import validate_project


@click.command()
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed validation information",
)
def check(verbose: bool) -> None:
    """Validate installed kit artifacts."""
    project_dir = Path.cwd()

    results = validate_project(project_dir)

    if len(results) == 0:
        click.echo("No artifacts found to validate")
        return

    valid_count = sum(1 for r in results if r.is_valid)
    invalid_count = len(results) - valid_count

    # Show results
    if verbose or invalid_count > 0:
        for result in results:
            status = "✓" if result.is_valid else "✗"
            rel_path = result.artifact_path.relative_to(project_dir)
            click.echo(f"{status} {rel_path}")

            if not result.is_valid:
                for error in result.errors:
                    click.echo(f"  - {error}", err=True)

    # Summary
    click.echo()
    click.echo(f"Validated {len(results)} artifacts:")
    click.echo(f"  ✓ Valid: {valid_count}")

    if invalid_count > 0:
        click.echo(f"  ✗ Invalid: {invalid_count}", err=True)
        raise SystemExit(1)
    else:
        click.echo("All artifacts are valid!")
