"""I/O operations for dot-agent-kit."""

from dot_agent_kit.io.discovery import (
    discover_all_artifacts,
    discover_installed_artifacts,
)
from dot_agent_kit.io.frontmatter import parse_user_metadata
from dot_agent_kit.io.manifest import load_kit_manifest
from dot_agent_kit.io.registry import load_registry
from dot_agent_kit.io.state import (
    create_default_config,
    load_project_config,
    save_project_config,
)

__all__ = [
    "create_default_config",
    "discover_all_artifacts",
    "discover_installed_artifacts",
    "load_kit_manifest",
    "load_project_config",
    "load_registry",
    "parse_user_metadata",
    "save_project_config",
]
