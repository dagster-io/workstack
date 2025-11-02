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
        # Read JSON input from stdin (not used, but validates format)
        json.load(sys.stdin)

        # Always output suggestion (runs on every prompt)
        print("<reminder>")
        print(
            "CRITICAL: Load dignified-python skill when editing Python and "
            "strictly abide by the standards defined in it."
        )
        print()
        print("Core philosophy:")
        print("  - Explicit, predictable code that fails fast")
        print("  - LBYL over EAFP - check before acting")
        print("  - Python 3.13+ syntax only")
        print("  - Error boundaries at CLI/API level")
        print()
        print("Critical rules:")
        print("  1. Exceptions: LBYL over EAFP 🔴")
        print(
            "     - ALWAYS use LBYL (Look Before You Leap) first, before EAFP, "
            "which should be used only if absolutely necessary "
            "(only API supported by 3rd party library, for example)"
        )
        print("     - Check conditions with if statements before acting")
        print("     - Only handle exceptions at error boundaries (CLI, third-party APIs)")
        print("     - Let exceptions bubble up by default")
        print(
            "  2. Types: Use list[str], dict[str,int], str|None. "
            "FORBIDDEN: List, Optional, Union 🔴"
        )
        print("  3. Imports: Absolute only. NEVER relative imports 🔴")
        print("  4. Style: Max 4 indent levels. Extract helpers if deeper")
        print("  5. Data: Prefer immutable data structures. Default to @dataclass(frozen=True)")
        print()
        print("See full skill for details")
        print("</reminder>")

        # Exit 0 to allow prompt to proceed
        # For UserPromptSubmit, stdout is injected as context for Claude
        sys.exit(0)

    except Exception as e:
        # Print error for debugging but don't block workflow
        print(f"dignified-python hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
