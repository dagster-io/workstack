#!/usr/bin/env python3
"""Example pre-tool hook script.

This demonstrates a simple hook that logs when Bash tool is about to be used.
Context is provided via stdin as JSON.

Example context structure for PreToolUse lifecycle:
{
    "tool": "Bash",
    "command": "ls -la",
    "description": "List files in current directory",
    "timeout": 120000,
    ...additional tool-specific parameters...
}

For Write tool:
{
    "tool": "Write",
    "file_path": "/path/to/file.py",
    "content": "print('hello')",
    ...
}

For Read tool:
{
    "tool": "Read",
    "file_path": "/path/to/file.py",
    "offset": 0,
    "limit": 100,
    ...
}
"""

import json
import sys


def main() -> int:
    """Main entry point for the hook."""
    try:
        # Read context from stdin
        # The context structure varies by tool type (see examples in docstring above)
        context = json.loads(sys.stdin.read())

        # Log the hook execution
        tool_name = context.get("tool", "unknown")
        print(f"[Example Hook] Pre-tool hook triggered for: {tool_name}", file=sys.stderr)

        # You could add validation, logging, or other pre-processing here
        return 0

    except Exception as e:
        print(f"[Example Hook] Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
