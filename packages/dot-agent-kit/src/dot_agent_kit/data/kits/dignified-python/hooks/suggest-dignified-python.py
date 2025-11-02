#!/usr/bin/env python3
"""
Dignified Python Skill Suggestion Hook

Injects dignified-python skill suggestion on every user prompt.
This ensures Claude always has access to Python coding standards.
"""

import json
import sys


def main():
    try:
        # Read JSON input from stdin
        data = json.load(sys.stdin)

        # Always output suggestion (runs on every prompt)
        print("Load the dignified-python skill to abide by Python standards")

        # Exit 0 to allow prompt to proceed
        # For UserPromptSubmit, stdout is injected as context for Claude
        sys.exit(0)

    except Exception as e:
        # Print error for debugging but don't block workflow
        print(f"dignified-python hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
