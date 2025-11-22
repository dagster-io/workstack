"""Tests for issue title to filename conversion."""

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.issue_title_to_filename import (
    title_to_filename,
)


def test_basic_title() -> None:
    """Convert simple title to kebab-case."""
    assert title_to_filename("Replace gt sync with targeted restack") == (
        "replace-gt-sync-with-targeted-restack-plan.md"
    )


def test_special_characters() -> None:
    """Remove special characters."""
    assert title_to_filename("Fix: Bug #123!") == "fix-bug-123-plan.md"


def test_consecutive_hyphens() -> None:
    """Collapse multiple hyphens."""
    assert title_to_filename("Feature  ---  Implementation") == ("feature-implementation-plan.md")


def test_leading_trailing_hyphens() -> None:
    """Strip leading and trailing hyphens."""
    assert title_to_filename("---Fix Bug---") == "fix-bug-plan.md"


def test_emoji() -> None:
    """Remove emojis."""
    assert title_to_filename("🚀 Awesome Feature!") == "awesome-feature-plan.md"


def test_empty_after_cleanup() -> None:
    """Empty string after cleanup returns plan.md."""
    assert title_to_filename("!!!") == "plan.md"
    assert title_to_filename("") == "plan.md"
    assert title_to_filename("   ") == "plan.md"


def test_unicode() -> None:
    """Handle unicode characters."""
    assert title_to_filename("Café Feature") == "caf-feature-plan.md"


def test_long_title() -> None:
    """Long titles are NOT truncated by kit command."""
    long_title = "Very Long Feature Name With Many Words That Exceeds Thirty Characters"
    result = title_to_filename(long_title)
    # Should NOT be truncated - erk create handles that
    assert len(result) > 30
    assert result.endswith("-plan.md")
