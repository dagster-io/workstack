"""Init command for creating dot-agent.toml configuration."""

from pathlib import Path

import click

from dot_agent_kit.io import create_default_config, save_project_config


@click.command()
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing dot-agent.toml if present",
)
def init(force: bool) -> None:
    """Initialize dot-agent.toml configuration file.

    Creates a new dot-agent.toml configuration file in the current directory.
    Also creates .claude/ directory if it doesn't exist.

    Use --force to overwrite an existing configuration.
    """
    project_dir = Path.cwd()
    config_path = project_dir / "dot-agent.toml"
    claude_dir = project_dir / ".claude"

    # Check if config already exists
    if config_path.exists() and not force:
        click.echo("Error: dot-agent.toml already exists", err=True)
        click.echo("Use --force to overwrite", err=True)
        raise SystemExit(1)

    # Create .claude directory if it doesn't exist
    if not claude_dir.exists():
        claude_dir.mkdir(parents=True)
        click.echo(f"Created {claude_dir}/")

    # Create default config
    config = create_default_config()
    save_project_config(project_dir, config)

    click.echo(f"Created {config_path}")
    click.echo("\nYou can now install kits using:")
    click.echo("  dot-agent kit install <kit-name>")
