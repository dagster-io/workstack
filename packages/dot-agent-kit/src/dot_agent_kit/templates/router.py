#!/usr/bin/env python3
"""Hook router for dot-agent-kit.

This script is installed to .claude/.dot-agent/router.py during dot-agent init.
It discovers and executes hooks from installed kits based on lifecycle events.

The router:
1. Scans .claude/.dot-agent/hooks/<kit-name>/ directories for hooks.toml files
2. Matches hooks against the current lifecycle event and context
3. Executes matching hook scripts in priority order
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python < 3.11


def discover_hook_configs(hooks_dir: Path, lifecycle: str) -> list[dict]:
    """Discover and load hook configurations for a specific lifecycle event.

    Args:
        hooks_dir: Path to .claude/.dot-agent/hooks/ directory
        lifecycle: Lifecycle event name (e.g., "PreToolUse", "PostToolUse")

    Returns:
        List of hook configurations matching the lifecycle
    """
    hooks = []

    if not hooks_dir.exists():
        return hooks

    # Scan each kit directory
    for kit_dir in hooks_dir.iterdir():
        if not kit_dir.is_dir():
            continue

        hooks_toml = kit_dir / "hooks.toml"
        if not hooks_toml.exists():
            continue

        try:
            with open(hooks_toml, "rb") as f:
                manifest = tomllib.load(f)

            # Extract hooks matching this lifecycle
            for hook in manifest.get("hooks", []):
                if not hook.get("enabled", True):
                    continue

                if hook.get("lifecycle") == lifecycle:
                    hooks.append(
                        {
                            "kit_id": manifest.get("kit_id"),
                            "kit_dir": kit_dir,
                            "name": hook.get("name"),
                            "matcher": hook.get("matcher"),
                            "script": hook.get("script"),
                            "description": hook.get("description"),
                        }
                    )
        except Exception as e:
            # Log but don't crash - one bad config shouldn't break everything
            print(f"Warning: Failed to load hooks from {kit_dir}: {e}", file=sys.stderr)
            continue

    return hooks


def matches_pattern(matcher: str, context: dict) -> bool:
    """Check if a hook matcher matches the current context.

    Args:
        matcher: Regex pattern to match against context
        context: Context dictionary from Claude Code

    Returns:
        True if the pattern matches
    """
    if not matcher:
        return True  # Empty matcher = always match

    # Convert context to JSON string for pattern matching
    context_str = json.dumps(context)

    try:
        pattern = re.compile(matcher)
        return pattern.search(context_str) is not None
    except re.error as e:
        print(f"Warning: Invalid regex pattern '{matcher}': {e}", file=sys.stderr)
        return False


def execute_hook(hook: dict, context: dict) -> bool:
    """Execute a hook script.

    Args:
        hook: Hook configuration dictionary
        context: Context dictionary from Claude Code

    Returns:
        True if execution succeeded, False otherwise
    """
    kit_dir = hook["kit_dir"]
    script_path = kit_dir / hook["script"]

    if not script_path.exists():
        print(
            f"Warning: Hook script not found: {script_path}",
            file=sys.stderr,
        )
        return False

    try:
        # Pass context as JSON via stdin
        context_json = json.dumps(context)

        result = subprocess.run(
            [sys.executable, str(script_path)],
            input=context_json,
            capture_output=True,
            text=True,
            check=True,
        )

        # Print hook output
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)

        return True

    except subprocess.CalledProcessError as e:
        print(
            f"Error executing hook '{hook['name']}' from {hook['kit_id']}: {e}",
            file=sys.stderr,
        )
        if e.stdout:
            print(e.stdout, end="", file=sys.stderr)
        if e.stderr:
            print(e.stderr, end="", file=sys.stderr)
        return False
    except Exception as e:
        print(
            f"Unexpected error executing hook '{hook['name']}': {e}",
            file=sys.stderr,
        )
        return False


def main() -> int:
    """Main entry point for the hook router."""
    parser = argparse.ArgumentParser(description="Dot-agent hook router")
    parser.add_argument(
        "--lifecycle",
        required=True,
        help="Lifecycle event name (e.g., PreToolUse, PostToolUse)",
    )
    args = parser.parse_args()

    # Determine hooks directory (should be .claude/.dot-agent/hooks/)
    script_dir = Path(__file__).parent
    hooks_dir = script_dir / "hooks"

    # Read context from stdin
    try:
        context = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON context from stdin: {e}", file=sys.stderr)
        return 1

    # Discover hooks for this lifecycle
    hooks = discover_hook_configs(hooks_dir, args.lifecycle)

    if not hooks:
        # No hooks to execute - this is not an error
        return 0

    # Filter hooks by matcher
    matching_hooks = [h for h in hooks if matches_pattern(h.get("matcher", ""), context)]

    # Execute matching hooks
    success_count = 0
    for hook in matching_hooks:
        if execute_hook(hook, context):
            success_count += 1

    # Return 0 (success) even if some hooks failed - don't block Claude Code
    return 0


if __name__ == "__main__":
    sys.exit(main())
