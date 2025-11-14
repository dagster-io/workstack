"""Init command for creating dot-agent.toml configuration."""

from pathlib import Path

import click

from dot_agent_kit.cli.output import user_output
from dot_agent_kit.io import create_default_config, save_project_config
from dot_agent_kit.io.registry import (
    ensure_agents_md_has_registry_reference,
    generate_doc_registry_content,
)


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
    Also creates .claude/ directory, kit registry, and AGENTS.md with registry reference.

    What gets created:
    - dot-agent.toml: Configuration file for tracking installed kits
    - .claude/: Directory for Claude Code artifacts
    - .claude/docs/kit-registry.md: Empty kit documentation registry
    - AGENTS.md: Agent instructions file with registry reference (or updates existing)

    Use --force to overwrite an existing configuration.
    """
    project_dir = Path.cwd()
    config_path = project_dir / "dot-agent.toml"
    claude_dir = project_dir / ".claude"

    # Check if config already exists
    if config_path.exists() and not force:
        user_output("Error: dot-agent.toml already exists")
        user_output("Use --force to overwrite")
        raise SystemExit(1)

    # Create .claude directory if it doesn't exist
    if not claude_dir.exists():
        claude_dir.mkdir(parents=True)
        user_output(f"Created {claude_dir}/")

    # Create empty kit registry file
    registry_dir = claude_dir / "docs"
    if not registry_dir.exists():
        registry_dir.mkdir(parents=True, exist_ok=True)

    registry_file = registry_dir / "kit-registry.md"
    registry_content = generate_doc_registry_content([])
    registry_file.write_text(registry_content, encoding="utf-8")
    user_output("Created kit registry")

    # Create default config
    config = create_default_config()
    save_project_config(project_dir, config)

    user_output(f"Created {config_path}")

    # Ensure AGENTS.md has registry reference
    status = ensure_agents_md_has_registry_reference(project_dir)
    if status == "created":
        user_output("Created AGENTS.md with kit registry reference")
    elif status == "updated":
        user_output("Updated AGENTS.md with kit registry reference")
    # If status == "exists", no output needed (already present)

    user_output("\nYou can now install kits using:")
    user_output("  dot-agent kit install <kit-name>")
