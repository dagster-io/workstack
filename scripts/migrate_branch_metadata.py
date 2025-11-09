#!/usr/bin/env python3
"""Migrate BranchMetadata constructor calls to helper methods.

This script uses regex to identify and migrate BranchMetadata constructor
calls to use the new .main() and .branch() helper methods.

Usage:
    python scripts/migrate_branch_metadata.py <file_path>
"""

import re
import sys
from pathlib import Path


def migrate_branch_metadata_calls(content: str) -> str:
    """Migrate BranchMetadata constructor calls in content."""
    # Pattern to match BranchMetadata constructor calls
    # This matches multi-line constructor calls with keyword arguments
    pattern = r"BranchMetadata\(((?:[^()]|\([^)]*\))*?)\)"

    def replace_call(match: re.Match) -> str:
        """Replace a single BranchMetadata constructor call."""
        args_str = match.group(1)

        # Parse keyword arguments
        kwargs = parse_kwargs(args_str)

        # Check for edge case: children=None (preserve direct constructor)
        if "children" in kwargs and kwargs["children"].strip() == "None":
            return match.group(0)  # Return original unchanged

        # Determine if trunk or feature branch
        is_trunk = kwargs.get("is_trunk", "").strip()

        if is_trunk == "True":
            # Trunk branch: migrate to BranchMetadata.main()
            return create_main_call(kwargs)
        if is_trunk == "False":
            # Feature branch: migrate to BranchMetadata.branch()
            return create_branch_call(kwargs)

        # If we can't determine the type, preserve original
        return match.group(0)

    return re.sub(pattern, replace_call, content, flags=re.DOTALL)


def parse_kwargs(args_str: str) -> dict[str, str]:
    """Parse keyword arguments from a string.

    This is a simple parser that handles basic cases.
    It may not handle all edge cases perfectly.
    """
    kwargs = {}

    # Split by commas, but be careful about commas inside brackets/parens
    parts = []
    current = ""
    depth = 0

    for char in args_str:
        if char in "([{":
            depth += 1
            current += char
        elif char in ")]}":
            depth -= 1
            current += char
        elif char == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += char

    if current.strip():
        parts.append(current.strip())

    # Parse each part as key=value
    for part in parts:
        part = part.strip()
        if "=" in part:
            key, value = part.split("=", 1)
            kwargs[key.strip()] = value.strip()

    return kwargs


def create_main_call(kwargs: dict[str, str]) -> str:
    """Create a BranchMetadata.main() call from kwargs."""
    parts = []

    # name is positional (but optional, defaults to "main")
    name = kwargs.get("name", "").strip()
    if name and name != '"main"' and name != "'main'":
        parts.append(name)

    # children and sha are keyword-only
    if "children" in kwargs:
        children = kwargs["children"].strip()
        if children != "[]":  # Only include if not empty list
            parts.append(f"children={children}")

    if "commit_sha" in kwargs:
        sha = kwargs["commit_sha"]
        parts.append(f"sha={sha}")

    args = ", ".join(parts)
    return f"BranchMetadata.main({args})"


def create_branch_call(kwargs: dict[str, str]) -> str:
    """Create a BranchMetadata.branch() call from kwargs."""
    parts = []

    # name is required positional
    if "name" in kwargs:
        parts.append(kwargs["name"].strip())

    # parent, children, and sha are keyword-only
    parent = kwargs.get("parent", "").strip()
    if parent and parent != '"main"' and parent != "'main'":
        parts.append(f"parent={parent}")

    if "children" in kwargs:
        children = kwargs["children"].strip()
        if children != "[]":  # Only include if not empty list
            parts.append(f"children={children}")

    if "commit_sha" in kwargs:
        sha = kwargs["commit_sha"]
        parts.append(f"sha={sha}")

    args = ", ".join(parts)
    return f"BranchMetadata.branch({args})"


def migrate_file(file_path: Path) -> None:
    """Migrate BranchMetadata calls in a single file."""
    if not file_path.exists():
        msg = f"File not found: {file_path}"
        raise FileNotFoundError(msg)

    # Read original content
    content = file_path.read_text(encoding="utf-8")

    # Migrate
    new_content = migrate_branch_metadata_calls(content)

    # Write back to file
    file_path.write_text(new_content, encoding="utf-8")

    print(f"✅ Migrated: {file_path}")


def main() -> None:
    """Main entry point for the migration script."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/migrate_branch_metadata.py <file_path>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    migrate_file(file_path)


if __name__ == "__main__":
    main()
