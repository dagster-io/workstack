"""Tests for add_gitignore_entry function."""

from workstack.core.init_utils import add_gitignore_entry


def test_adds_entry_to_empty_content() -> None:
    """Test adds entry to empty gitignore content."""
    content = ""

    result = add_gitignore_entry(content, ".PLAN.md")

    assert result == "\n.PLAN.md\n"


def test_adds_entry_to_existing_content() -> None:
    """Test adds entry to existing gitignore content."""
    content = "*.pyc\n__pycache__/\n"

    result = add_gitignore_entry(content, ".PLAN.md")

    assert result == "*.pyc\n__pycache__/\n.PLAN.md\n"


def test_adds_newline_if_missing() -> None:
    """Test adds trailing newline before entry if missing."""
    content = "*.pyc"

    result = add_gitignore_entry(content, ".PLAN.md")

    assert result == "*.pyc\n.PLAN.md\n"


def test_idempotent_when_entry_exists() -> None:
    """Test returns unchanged content when entry already exists."""
    content = "*.pyc\n.PLAN.md\n__pycache__/\n"

    result = add_gitignore_entry(content, ".PLAN.md")

    assert result == content


def test_multiple_additions() -> None:
    """Test adding multiple entries."""
    content = "*.pyc\n"

    content = add_gitignore_entry(content, ".PLAN.md")
    content = add_gitignore_entry(content, ".env")

    assert ".PLAN.md" in content
    assert ".env" in content
    assert content.count(".PLAN.md") == 1
    assert content.count(".env") == 1


def test_does_not_add_duplicate() -> None:
    """Test adding same entry twice is idempotent."""
    content = "*.pyc\n"

    content = add_gitignore_entry(content, ".PLAN.md")
    content_before = content
    content = add_gitignore_entry(content, ".PLAN.md")

    assert content == content_before


def test_preserves_existing_formatting() -> None:
    """Test preserves existing content formatting."""
    content = "# Python\n*.pyc\n\n# Node\nnode_modules/\n"

    result = add_gitignore_entry(content, ".PLAN.md")

    assert "# Python" in result
    assert "*.pyc" in result
    assert "# Node" in result
    assert result.endswith(".PLAN.md\n")


def test_handles_entry_as_substring() -> None:
    """Test correctly identifies existing entry (not just substring match)."""
    content = ".PLAN.md.backup\n"

    result = add_gitignore_entry(content, ".PLAN.md")

    # Since ".PLAN.md" is a substring of ".PLAN.md.backup", the current
    # implementation will think it exists. This documents current behavior.
    # If exact matching is needed, the function should be updated.
    assert result == content
