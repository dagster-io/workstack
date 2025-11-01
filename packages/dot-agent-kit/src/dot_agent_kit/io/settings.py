"""Settings.json I/O for Claude Code settings."""

import json
from pathlib import Path


def load_settings(settings_path: Path) -> dict:
    """Load settings.json from Claude Code config directory.

    Returns empty dict if file doesn't exist.
    """
    if not settings_path.exists():
        return {}

    with open(settings_path, encoding="utf-8") as f:
        return json.load(f)


def save_settings(settings_path: Path, settings: dict) -> None:
    """Save settings.json to Claude Code config directory."""
    # Ensure parent directory exists
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")  # Add trailing newline


def ensure_router_hooks(settings_path: Path, router_path: Path) -> bool:
    """Ensure router hooks are registered in settings.json.

    This is idempotent - only adds router entries if they don't exist.

    Args:
        settings_path: Path to settings.json
        router_path: Path to router.py script

    Returns:
        True if settings were modified, False if already present
    """
    settings = load_settings(settings_path)

    # Define router hook entries
    lifecycles = [
        "PreToolUse",
        "PostToolUse",
        "PreUserMessage",
        "PostUserMessage",
    ]

    # Ensure hooks section exists
    if "hooks" not in settings:
        settings["hooks"] = {}

    modified = False

    for lifecycle in lifecycles:
        # Ensure lifecycle section exists
        if lifecycle not in settings["hooks"]:
            settings["hooks"][lifecycle] = []

        # Check if router already registered
        router_entry = {
            "command": f"python3 {router_path} --lifecycle {lifecycle}",
            "description": f"Dot-agent hook router for {lifecycle}",
        }

        # Check if an equivalent entry exists
        already_exists = False
        for hook in settings["hooks"][lifecycle]:
            if isinstance(hook, dict) and hook.get("command", "").endswith(
                f"router.py --lifecycle {lifecycle}"
            ):
                already_exists = True
                break

        if not already_exists:
            settings["hooks"][lifecycle].append(router_entry)
            modified = True

    if modified:
        save_settings(settings_path, settings)

    return modified
