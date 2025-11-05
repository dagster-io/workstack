#!/usr/bin/env python3
"""
Dignified Python Skill Suggestion Hook

Injects dignified-python skill suggestion on every user prompt.
This ensures Claude always has access to Python coding standards.
"""

import json
import os
import sys
from pathlib import Path


def get_fallback_message() -> str:
    """Return hardcoded fallback message if SKILL.md is not found."""
    return """CRITICAL: Load dignified-python skill when editing Python and strictly
abide by the standards defined in it.

Core philosophy:
  - Explicit, predictable code that fails fast
  - LBYL over EAFP - check before acting
  - Python 3.13+ syntax only
  - Error boundaries at CLI/API level

Critical rules:
  1. Exceptions: LBYL over EAFP 🔴
     - ALWAYS use LBYL (Look Before You Leap) first, before EAFP, which
       should be used only if absolutely necessary (only API supported by
       3rd party library, for example)
     - Check conditions with if statements before acting
     - Only handle exceptions at error boundaries (CLI, third-party APIs)
     - Let exceptions bubble up by default
  2. Types: Use list[str], dict[str,int], str|None. FORBIDDEN: List, Optional, Union 🔴
  3. Imports: Absolute only. NEVER relative imports 🔴
  4. Style: Max 4 indent levels. Extract helpers if deeper
  5. Data: Prefer immutable data structures. Default to @dataclass(frozen=True)
  6. NO fallback behavior: Fail fast, don't silently degrade 🔴

See full skill for details"""


def read_skill_content() -> str:
    """Read dignified-python SKILL.md content, or return fallback if not found."""
    # Get project directory from environment (LBYL: check env var exists)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project_dir:
        print(
            "Warning: CLAUDE_PROJECT_DIR not set, using fallback message",
            file=sys.stderr,
        )
        return get_fallback_message()

    # Construct path to SKILL.md (LBYL: check file exists)
    skill_path = Path(project_dir) / ".claude" / "skills" / "dignified-python" / "SKILL.md"
    if not skill_path.exists():
        print(
            f"Warning: SKILL.md not found at {skill_path}, using fallback message",
            file=sys.stderr,
        )
        return get_fallback_message()

    # Read and return file contents
    return skill_path.read_text(encoding="utf-8")


def main():
    try:
        # Read JSON input from stdin (not used, but validates format)
        json.load(sys.stdin)

        # Get skill content (from SKILL.md or fallback)
        skill_content = read_skill_content()

        # Always output suggestion (runs on every prompt)
        print("<reminder>")
        print(skill_content)
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
