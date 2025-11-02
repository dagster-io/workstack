#!/usr/bin/env python3
"""
Dignified Python Skill Suggestion Hook

Suggests loading the dignified-python skill when editing Python files.
This provides Claude with workstack's Python coding standards.
"""

import json
import sys


def main():
    try:
        # Read JSON input from stdin
        data = json.load(sys.stdin)

        # Extract tool information
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        # Only trigger for Edit/Write operations on Python files
        if not (file_path.endswith(".py") and tool_name in ["Edit", "Write"]):
            sys.exit(0)

        # Skip test files (different patterns acceptable)
        skip_patterns = ["test_", "_test.py", "conftest.py", "/tests/", "/migrations/"]
        if any(pattern in file_path.lower() for pattern in skip_patterns):
            sys.exit(0)

        # Output suggestion to load skill
        print("Load the dignified-python skill to abide by Python standards")

        # Exit 0 to allow operation to proceed (non-blocking)
        sys.exit(0)

    except Exception as e:
        # Print error for debugging but don't block workflow
        print(f"dignified-python hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
