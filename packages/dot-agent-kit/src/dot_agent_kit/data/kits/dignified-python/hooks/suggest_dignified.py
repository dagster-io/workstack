#!/usr/bin/env python3
"""Dignified Python Skill Suggestion Hook.

This hook suggests loading the dignified-python skill when editing Python files.
It demonstrates the PreToolUse hook lifecycle for educational purposes.

HOOK STRUCTURE:
1. Read JSON input from stdin containing tool_name and tool_input
2. Check if this is a file operation we care about
3. Apply filtering logic to exclude certain file types
4. Output suggestion message if conditions are met
5. Exit with code 0 to allow the operation to proceed (non-blocking)

HOOK LIFECYCLE:
- PreToolUse hooks run BEFORE a tool executes
- They receive tool_name and tool_input as JSON on stdin
- They can output messages to suggest skills or provide guidance
- Exit code 0 = allow operation to proceed
- Exit code 1 = block operation (use sparingly)

MATCHER PATTERN:
- This hook uses matcher "Edit|Write" in kit.toml
- It triggers when Claude uses Edit or Write tools
- The matcher is a pipe-separated list of tool names
"""

import json
import sys


def main():
    """Main hook entry point.

    Hook execution flow:
    1. Parse stdin JSON to get tool context
    2. Extract file path from tool input
    3. Check if this is a Python file we care about
    4. Skip test files and migrations
    5. Output skill suggestion if applicable
    6. Always exit 0 to be non-blocking
    """
    # Hooks should be defensive - catch all exceptions to avoid breaking workflows
    # This is one of the few acceptable uses of broad exception handling
    try:
        # Read JSON input from stdin
        # PreToolUse hooks receive:
        # {
        #   "tool_name": "Edit" | "Write" | ...,
        #   "tool_input": { "file_path": "...", ... }
        # }
        data = json.load(sys.stdin)

        # Extract tool information
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        # Only trigger for Edit/Write operations on Python files
        # The matcher in kit.toml already filters to Edit|Write,
        # but we double-check here for clarity
        if not (file_path.endswith(".py") and tool_name in ["Edit", "Write"]):
            sys.exit(0)

        # Skip test files (different patterns acceptable)
        # We want to suggest standards for production code, not tests
        # Tests have different patterns and are covered in tests/CLAUDE.md
        skip_patterns = ["test_", "_test.py", "conftest.py", "/tests/", "/migrations/"]
        if any(pattern in file_path.lower() for pattern in skip_patterns):
            sys.exit(0)

        # Output suggestion to load skill
        # This message appears in Claude's context as a system reminder
        # The skill provides detailed Python coding standards
        print("Load the dignified-python skill to abide by Python standards")

        # Exit 0 to allow operation to proceed (non-blocking)
        # PreToolUse hooks can be:
        # - Non-blocking (exit 0): Provide suggestions but allow operation
        # - Blocking (exit 1): Prevent operation from proceeding
        # This hook is non-blocking - it guides but doesn't enforce
        sys.exit(0)

    except Exception as e:
        # Print error for debugging but don't block workflow
        # Hook errors should never break the user's workflow
        # Errors are logged to stderr for troubleshooting
        print(f"dignified-python hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
