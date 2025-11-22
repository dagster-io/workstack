#!/usr/bin/env python3
"""Standalone script to remove all hooks from project-level settings.json.

This script:
1. Loads the project-level settings.json from .claude/settings.json
2. Removes all hooks while preserving permissions and other settings
3. Atomically writes the updated settings back to the file

Use Cases:
- Remove hooks when they are causing issues or blocking workflow
- Clean up hooks during merge conflicts in .claude/settings.json
- Emergency recovery when hook syntax errors prevent Claude Code from loading

Why Standalone:
This script is intentionally standalone (no dependencies on erk modules) so it can
run even when merge conflicts or syntax errors in .claude/ files prevent normal
tools from loading. It has zero dependencies beyond Python 3.10+ stdlib.

Usage:
    python scripts/remove_hooks.py
"""

import json
import sys
import tempfile
from pathlib import Path


def main() -> None:
    """Remove all hooks from project-level settings.json."""
    # Determine project root (script is in scripts/ folder, go up one level)
    project_root = Path(__file__).parent.parent
    settings_path = project_root / ".claude" / "settings.json"

    # Check if settings file exists
    if not settings_path.exists():
        print(f"✓ No settings file found at {settings_path}")
        print("  Nothing to do.")
        return

    # Load settings
    try:
        content = settings_path.read_text(encoding="utf-8")
        settings = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in {settings_path}")
        print(f"   {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading {settings_path}: {e}")
        sys.exit(1)

    # Check if hooks exist
    if "hooks" not in settings:
        print(f"✓ No hooks found in {settings_path}")
        print("  Nothing to do.")
        return

    # Count hooks before removal
    hook_count = 0
    if isinstance(settings.get("hooks"), dict):
        for _lifecycle, groups in settings["hooks"].items():
            if isinstance(groups, list):
                for group in groups:
                    if isinstance(group, dict) and "hooks" in group:
                        if isinstance(group["hooks"], list):
                            hook_count += len(group["hooks"])

    print(f"Found {hook_count} hook(s) to remove")

    # Remove hooks field
    del settings["hooks"]

    # Write atomically using temp file + rename
    try:
        # Ensure parent directory exists
        if not settings_path.parent.exists():
            settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Create temp file in same directory to ensure atomic rename works
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=settings_path.parent,
            delete=False,
            suffix=".tmp",
        ) as tmp:
            json.dump(settings, tmp, indent=2)
            tmp.write("\n")  # Add trailing newline
            tmp_path = Path(tmp.name)

        # Atomic rename
        tmp_path.replace(settings_path)

        print(f"✅ Successfully removed all hooks from {settings_path}")
        print(f"   Removed {hook_count} hook(s)")

    except Exception as e:
        print(f"❌ Error writing {settings_path}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
