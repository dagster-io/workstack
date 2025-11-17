"""Utility functions for naming and sanitization.

This module provides pure business logic functions for worktree and branch naming,
separated from I/O and CLI concerns. These functions work with strings and enable
fast unit testing without filesystem dependencies.
"""

import re
from datetime import datetime
from pathlib import Path

_SAFE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9._/-]+")


def sanitize_branch_component(name: str) -> str:
    """Return a sanitized, predictable branch component from an arbitrary name.

    - Lowercases input
    - Replaces characters outside `[A-Za-z0-9._/-]` with `-`
    - Collapses consecutive `-`
    - Strips leading/trailing `-` and `/`
    Returns `"work"` if the result is empty.

    Args:
        name: Arbitrary string to sanitize

    Returns:
        Sanitized branch component name

    Examples:
        >>> sanitize_branch_component("My Feature!")
        "my-feature"
        >>> sanitize_branch_component("fix/bug-123")
        "fix/bug-123"
        >>> sanitize_branch_component("")
        "work"
    """
    lowered = name.strip().lower()
    replaced = _SAFE_COMPONENT_RE.sub("-", lowered)
    collapsed = re.sub(r"-+", "-", replaced)
    trimmed = collapsed.strip("-/")
    result = trimmed or "work"

    return result


def sanitize_worktree_name(name: str) -> str:
    """Sanitize a worktree name for use as a directory name.

    - Lowercases input
    - Replaces underscores with hyphens
    - Replaces characters outside `[A-Za-z0-9.-]` with `-`
    - Collapses consecutive `-`
    - Strips leading/trailing `-`
    - Truncates to 30 characters maximum (matches branch component sanitization)
    Returns `"work"` if the result is empty.

    The 30-character limit ensures worktree names match their corresponding branch
    names, maintaining consistency across the worktree/branch model.

    Args:
        name: Arbitrary string to sanitize

    Returns:
        Sanitized worktree name (max 30 chars)

    Examples:
        >>> sanitize_worktree_name("My_Feature")
        "my-feature"
        >>> sanitize_worktree_name("a" * 40)
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"  # 30 chars
    """
    lowered = name.strip().lower()
    # Replace underscores with hyphens
    replaced_underscores = lowered.replace("_", "-")
    # Replace unsafe characters with hyphens
    replaced = re.sub(r"[^a-z0-9.-]+", "-", replaced_underscores)
    # Collapse consecutive hyphens
    collapsed = re.sub(r"-+", "-", replaced)
    # Strip leading/trailing hyphens
    trimmed = collapsed.strip("-")
    result = trimmed or "work"

    # Truncate to 30 characters and strip trailing hyphens
    if len(result) > 30:
        result = result[:30].rstrip("-")

    return result


def strip_plan_from_filename(filename: str) -> str:
    """Remove 'plan' or 'implementation plan' from a filename stem intelligently.

    Handles case-insensitive matching and common separators (-, _, space).
    If removal would leave empty string, returns original unchanged.

    Args:
        filename: Filename stem (without extension) to process

    Returns:
        Filename with plan-related words removed, or original if would be empty

    Examples:
        >>> strip_plan_from_filename("devclikit-extraction-plan")
        "devclikit-extraction"
        >>> strip_plan_from_filename("my-feature-plan")
        "my-feature"
        >>> strip_plan_from_filename("implementation-plan-for-auth")
        "for-auth"
        >>> strip_plan_from_filename("feature_implementation_plan")
        "feature"
        >>> strip_plan_from_filename("plan")
        "plan"  # preserved - would be empty
    """
    original_trimmed = filename.strip("-_ \t\n\r")
    original_is_plan = original_trimmed.casefold() == "plan" if original_trimmed else False

    # First, handle "implementation plan" with various separators
    # Pattern matches "implementation" + separator + "plan" as complete words
    impl_pattern = r"(^|[-_\s])(implementation)([-_\s])(plan)([-_\s]|$)"

    def replace_impl_plan(match: re.Match[str]) -> str:
        prefix = match.group(1)
        implementation_word = match.group(2)  # Preserves original case
        suffix = match.group(5)

        if suffix == "" and prefix:
            prefix_start = match.start(1)
            preceding_segment = filename[:prefix_start]
            trimmed_segment = preceding_segment.strip("-_ \t\n\r")
            if trimmed_segment:
                preceding_tokens = re.split(r"[-_\s]+", trimmed_segment)
                if preceding_tokens:
                    preceding_token = preceding_tokens[-1]
                    if preceding_token.casefold() == "plan":
                        return f"{prefix}{implementation_word}"

        # If entire string is "implementation-plan", keep just "implementation"
        if not prefix and not suffix:
            return implementation_word

        # If in the middle, preserve one separator
        if prefix and suffix:
            return prefix if prefix.strip() else suffix

        # At start or end: remove it and the adjacent separator
        return ""

    cleaned = re.sub(impl_pattern, replace_impl_plan, filename, flags=re.IGNORECASE)

    # Then handle standalone "plan" as a complete word
    plan_pattern = r"(^|[-_\s])(plan)([-_\s]|$)"

    def replace_plan(match: re.Match[str]) -> str:
        prefix = match.group(1)
        suffix = match.group(3)

        # If both prefix and suffix are empty (entire string is "plan"), keep it
        if not prefix and not suffix:
            return "plan"

        # If plan is in the middle, preserve one separator
        if prefix and suffix:
            # Use the prefix separator if available, otherwise use suffix
            return prefix if prefix.strip() else suffix

        # Plan at start or end: remove it and the adjacent separator
        return ""

    cleaned = re.sub(plan_pattern, replace_plan, cleaned, flags=re.IGNORECASE)

    def clean_separators(text: str) -> str:
        stripped = text.strip("-_ \t\n\r")
        stripped = re.sub(r"--+", "-", stripped)
        stripped = re.sub(r"__+", "_", stripped)
        stripped = re.sub(r"\s+", " ", stripped)
        return stripped

    cleaned = clean_separators(cleaned)

    plan_only_cleaned = clean_separators(
        re.sub(plan_pattern, replace_plan, filename, flags=re.IGNORECASE)
    )

    if (
        cleaned.casefold() == "plan"
        and plan_only_cleaned
        and plan_only_cleaned.casefold() != "plan"
    ):
        cleaned = plan_only_cleaned

    # If stripping left us with nothing or just "plan", preserve original
    if not cleaned or (cleaned.casefold() == "plan" and original_is_plan):
        return filename

    return cleaned


def extract_trailing_number(name: str) -> tuple[str, int | None]:
    r"""Extract trailing number from a name.

    Detects trailing numbers in names using regex pattern `^(.+?)-(\d+)$`.
    Returns tuple of (base_name, number) or (name, None).

    Args:
        name: Name to parse

    Returns:
        Tuple of (base_name, number) if trailing number found, else (name, None)

    Examples:
        >>> extract_trailing_number("my-feature")
        ("my-feature", None)
        >>> extract_trailing_number("my-feature-2")
        ("my-feature", 2)
        >>> extract_trailing_number("fix-42")
        ("fix", 42)
    """
    match = re.match(r"^(.+?)-(\d+)$", name)
    if match:
        base_name = match.group(1)
        number = int(match.group(2))
        return (base_name, number)
    return (name, None)


def ensure_unique_worktree_name(base_name: str, worktrees_dir: Path, git_ops) -> str:
    """Ensure unique worktree name with date suffix and smart versioning.

    Adds date suffix in format -YY-MM-DD to the base name.
    If a worktree with that name exists, increments numeric suffix starting at 2 AFTER the date.
    Uses LBYL pattern: checks via git_ops.path_exists() before operations.

    Args:
        base_name: Sanitized worktree base name (without date suffix)
        worktrees_dir: Directory containing worktrees
        git_ops: Git operations interface for checking path existence

    Returns:
        Guaranteed unique worktree name with date suffix

    Examples:
        First time: "my-feature" → "my-feature-25-11-08"
        Duplicate: "my-feature" → "my-feature-25-11-08-2"
        Next day: "my-feature" → "my-feature-25-11-09"
    """
    date_suffix = datetime.now().strftime("%y-%m-%d")
    candidate_name = f"{base_name}-{date_suffix}"

    # Check if the base candidate exists
    if not git_ops.path_exists(worktrees_dir / candidate_name):
        return candidate_name

    # Name exists, find next available number (append after date)
    counter = 2
    while True:
        versioned_name = f"{base_name}-{date_suffix}-{counter}"
        if not git_ops.path_exists(worktrees_dir / versioned_name):
            return versioned_name
        counter += 1


def default_branch_for_worktree(name: str) -> str:
    """Default branch name for a worktree with the given `name`.

    Returns the sanitized name directly (without any prefix).

    Args:
        name: Worktree name

    Returns:
        Default branch name (sanitized)

    Examples:
        >>> default_branch_for_worktree("my-feature")
        "my-feature"
        >>> default_branch_for_worktree("Fix Bug!")
        "fix-bug"
    """
    return sanitize_branch_component(name)
