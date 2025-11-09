"""File operation utilities."""

from pathlib import Path


def extract_plan_title(plan_path: Path) -> str | None:
    """Extract the first heading from a markdown plan file.

    Uses python-frontmatter library to properly parse YAML frontmatter,
    then extracts the first line starting with # from the content.
    Common prefixes like "Implementation Plan: " are stripped from the title.

    Args:
        plan_path: Path to the .PLAN.md file

    Returns:
        The heading text (without the # prefix and common prefixes), or None if
        not found or file doesn't exist
    """
    if not plan_path.exists():
        return None

    import frontmatter

    # Parse file with frontmatter library (handles YAML frontmatter properly)
    post = frontmatter.load(str(plan_path))

    # Get the content (without frontmatter)
    content = post.content
    lines = content.splitlines()

    # Common prefixes to strip from plan titles
    COMMON_PREFIXES = [
        "Implementation Plan: ",
        "Implementation Plan - ",
    ]

    # Find first heading
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            # Remove all # symbols and strip whitespace
            title = stripped.lstrip("#").strip()
            if title:
                # Strip common prefixes (case-insensitive)
                for prefix in COMMON_PREFIXES:
                    if title.lower().startswith(prefix.lower()):
                        title = title[len(prefix) :].strip()
                        break
                return title

    return None
