"""I/O operations for dot-agent-kit."""

from dot_agent_kit.io.discovery import (
    discover_all_artifacts,
    discover_installed_artifacts,
)
from dot_agent_kit.io.frontmatter import (
    add_frontmatter,
    parse_frontmatter,
    validate_frontmatter,
)
from dot_agent_kit.io.hook_manifest import (
    load_hook_manifest,
    save_hook_manifest,
    update_hook_enabled,
)
from dot_agent_kit.io.manifest import load_kit_manifest
from dot_agent_kit.io.registry import load_registry
from dot_agent_kit.io.settings import (
    ensure_router_hooks,
    load_settings,
    save_settings,
)
from dot_agent_kit.io.state import (
    create_default_config,
    load_project_config,
    save_project_config,
)
from dot_agent_kit.io.user_config import (
    create_default_user_config,
    get_user_claude_dir,
    get_user_config_path,
    load_user_config,
    save_user_config,
)

__all__ = [
    "add_frontmatter",
    "create_default_config",
    "create_default_user_config",
    "discover_all_artifacts",
    "discover_installed_artifacts",
    "ensure_router_hooks",
    "get_user_claude_dir",
    "get_user_config_path",
    "load_hook_manifest",
    "load_kit_manifest",
    "load_project_config",
    "load_registry",
    "load_settings",
    "load_user_config",
    "parse_frontmatter",
    "save_hook_manifest",
    "save_project_config",
    "save_settings",
    "save_user_config",
    "update_hook_enabled",
    "validate_frontmatter",
]
