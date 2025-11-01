#!/usr/bin/env python3
"""Example post-tool hook script.

This demonstrates a hook that runs after Write tool is used.
Context is provided via stdin as JSON.
"""

import json
import sys


def main() -> int:
    """Main entry point for the hook."""
    try:
        # Read context from stdin
        context = json.loads(sys.stdin.read())

        # Log the hook execution
        tool_name = context.get("tool", "unknown")
        print(f"[Example Hook] Post-tool hook triggered for: {tool_name}", file=sys.stderr)

        # You could add post-processing, notifications, or cleanup here
        return 0

    except Exception as e:
        print(f"[Example Hook] Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
