"""Tests for link validation module."""

from pathlib import Path

from dot_agent_kit.io.at_reference import AtReference
from dot_agent_kit.io.link_validation import (
    extract_anchors,
    heading_to_anchor,
    validate_at_reference,
    validate_links_in_file,
)


class TestHeadingToAnchor:
    """Tests for heading_to_anchor function."""

    def test_simple_heading(self) -> None:
        """Test simple heading conversion."""
        assert heading_to_anchor("## My Section") == "my-section"

    def test_heading_with_punctuation(self) -> None:
        """Test heading with punctuation removed."""
        assert heading_to_anchor("## What's New?") == "whats-new"

    def test_heading_with_multiple_hashes(self) -> None:
        """Test heading with different levels."""
        assert heading_to_anchor("# Title") == "title"
        assert heading_to_anchor("### Subsection") == "subsection"

    def test_heading_with_extra_spaces(self) -> None:
        """Test heading with extra spaces."""
        assert heading_to_anchor("##   Extra   Spaces  ") == "extra-spaces"

    def test_heading_preserves_numbers(self) -> None:
        """Test that numbers are preserved."""
        assert heading_to_anchor("## Section 1.2") == "section-12"

    def test_heading_multiple_hyphens_collapsed(self) -> None:
        """Test that multiple hyphens are collapsed."""
        assert heading_to_anchor("## A - B - C") == "a-b-c"

    def test_heading_special_characters_removed(self) -> None:
        """Test that special characters are removed."""
        assert heading_to_anchor("## Code & Examples!") == "code-examples"


class TestExtractAnchors:
    """Tests for extract_anchors function."""

    def test_extract_simple_headings(self, tmp_path: Path) -> None:
        """Test extracting anchors from simple headings."""
        md_file = tmp_path / "test.md"
        md_file.write_text(
            """# Title

## First Section

Some content.

## Second Section

More content.
""",
            encoding="utf-8",
        )

        anchors = extract_anchors(md_file)
        assert "title" in anchors
        assert "first-section" in anchors
        assert "second-section" in anchors

    def test_extract_from_nonexistent_file(self, tmp_path: Path) -> None:
        """Test extracting anchors from nonexistent file returns empty set."""
        nonexistent = tmp_path / "nonexistent.md"
        anchors = extract_anchors(nonexistent)
        assert anchors == set()

    def test_extract_no_headings(self, tmp_path: Path) -> None:
        """Test extracting anchors from file with no headings."""
        md_file = tmp_path / "test.md"
        md_file.write_text("Just some text without headings.", encoding="utf-8")

        anchors = extract_anchors(md_file)
        assert anchors == set()


class TestValidateAtReference:
    """Tests for validate_at_reference function."""

    def test_valid_file_reference(self, tmp_path: Path) -> None:
        """Test valid file reference passes validation."""
        # Create source file and target file
        source = tmp_path / "CLAUDE.md"
        source.write_text("@AGENTS.md", encoding="utf-8")
        target = tmp_path / "AGENTS.md"
        target.write_text("# Agents Guide", encoding="utf-8")

        ref = AtReference(
            raw_text="@AGENTS.md",
            file_path="AGENTS.md",
            fragment=None,
            line_number=1,
        )

        broken = validate_at_reference(ref, source, tmp_path)
        assert broken == []

    def test_broken_file_reference(self, tmp_path: Path) -> None:
        """Test missing file is detected."""
        source = tmp_path / "CLAUDE.md"
        source.write_text("@nonexistent.md", encoding="utf-8")

        ref = AtReference(
            raw_text="@nonexistent.md",
            file_path="nonexistent.md",
            fragment=None,
            line_number=1,
        )

        broken = validate_at_reference(ref, source, tmp_path)
        assert len(broken) == 1
        assert broken[0].error_type == "missing_file"

    def test_valid_fragment(self, tmp_path: Path) -> None:
        """Test valid fragment passes validation."""
        source = tmp_path / "CLAUDE.md"
        source.write_text("@docs.md#installation", encoding="utf-8")
        target = tmp_path / "docs.md"
        target.write_text("# Guide\n\n## Installation\n\nContent.", encoding="utf-8")

        ref = AtReference(
            raw_text="@docs.md#installation",
            file_path="docs.md",
            fragment="installation",
            line_number=1,
        )

        broken = validate_at_reference(ref, source, tmp_path)
        assert broken == []

    def test_broken_fragment(self, tmp_path: Path) -> None:
        """Test missing heading/fragment is detected."""
        source = tmp_path / "CLAUDE.md"
        source.write_text("@docs.md#nonexistent", encoding="utf-8")
        target = tmp_path / "docs.md"
        target.write_text("# Guide\n\n## Installation\n\nContent.", encoding="utf-8")

        ref = AtReference(
            raw_text="@docs.md#nonexistent",
            file_path="docs.md",
            fragment="nonexistent",
            line_number=1,
        )

        broken = validate_at_reference(ref, source, tmp_path)
        assert len(broken) == 1
        assert broken[0].error_type == "missing_fragment"
        assert broken[0].error_detail == "nonexistent"

    def test_missing_file_and_fragment_reports_both(self, tmp_path: Path) -> None:
        """Test that both file and fragment errors are reported."""
        source = tmp_path / "CLAUDE.md"
        source.write_text("@nonexistent.md#section", encoding="utf-8")

        ref = AtReference(
            raw_text="@nonexistent.md#section",
            file_path="nonexistent.md",
            fragment="section",
            line_number=1,
        )

        broken = validate_at_reference(ref, source, tmp_path)
        assert len(broken) == 2
        error_types = {b.error_type for b in broken}
        assert "missing_file" in error_types
        assert "missing_fragment" in error_types

    def test_relative_path_resolution(self, tmp_path: Path) -> None:
        """Test relative paths are resolved from source file directory."""
        # Create directory structure
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        source = docs_dir / "guide.md"
        source.write_text("@../README.md", encoding="utf-8")

        target = tmp_path / "README.md"
        target.write_text("# README", encoding="utf-8")

        ref = AtReference(
            raw_text="@../README.md",
            file_path="../README.md",
            fragment=None,
            line_number=1,
        )

        broken = validate_at_reference(ref, source, tmp_path)
        assert broken == []

    def test_home_directory_path_skipped(self, tmp_path: Path) -> None:
        """Test home directory paths are skipped (not validated)."""
        source = tmp_path / "CLAUDE.md"
        source.write_text("@~/.claude/settings.md", encoding="utf-8")

        ref = AtReference(
            raw_text="@~/.claude/settings.md",
            file_path="~/.claude/settings.md",
            fragment=None,
            line_number=1,
        )

        broken = validate_at_reference(ref, source, tmp_path)
        assert broken == []

    def test_shell_variable_path_skipped(self, tmp_path: Path) -> None:
        """Test shell variable paths are skipped (not validated)."""
        source = tmp_path / "CLAUDE.md"
        source.write_text("@$HOME/.claude/settings.md", encoding="utf-8")

        ref = AtReference(
            raw_text="@$HOME/.claude/settings.md",
            file_path="$HOME/.claude/settings.md",
            fragment=None,
            line_number=1,
        )

        broken = validate_at_reference(ref, source, tmp_path)
        assert broken == []


class TestValidateLinksInFile:
    """Tests for validate_links_in_file function."""

    def test_file_with_valid_links(self, tmp_path: Path) -> None:
        """Test file with all valid links."""
        source = tmp_path / "CLAUDE.md"
        source.write_text(
            """@AGENTS.md

Some content.

@docs/guide.md
""",
            encoding="utf-8",
        )

        (tmp_path / "AGENTS.md").write_text("# Agents", encoding="utf-8")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "guide.md").write_text("# Guide", encoding="utf-8")

        broken = validate_links_in_file(source, tmp_path)
        assert broken == []

    def test_file_with_broken_links(self, tmp_path: Path) -> None:
        """Test file with broken links."""
        source = tmp_path / "CLAUDE.md"
        source.write_text(
            """@missing1.md

@missing2.md#section
""",
            encoding="utf-8",
        )

        broken = validate_links_in_file(source, tmp_path)
        # missing1.md: 1 error (missing_file)
        # missing2.md#section: 2 errors (missing_file, missing_fragment)
        assert len(broken) == 3

    def test_nonexistent_source_file(self, tmp_path: Path) -> None:
        """Test validating nonexistent source file returns empty list."""
        nonexistent = tmp_path / "nonexistent.md"
        broken = validate_links_in_file(nonexistent, tmp_path)
        assert broken == []

    def test_file_with_no_references(self, tmp_path: Path) -> None:
        """Test file with no @ references."""
        source = tmp_path / "CLAUDE.md"
        source.write_text("Just some text.", encoding="utf-8")

        broken = validate_links_in_file(source, tmp_path)
        assert broken == []

    def test_mixed_valid_and_broken_links(self, tmp_path: Path) -> None:
        """Test file with mix of valid and broken links."""
        source = tmp_path / "CLAUDE.md"
        source.write_text(
            """@AGENTS.md

@missing.md

@docs/guide.md#installation
""",
            encoding="utf-8",
        )

        (tmp_path / "AGENTS.md").write_text("# Agents", encoding="utf-8")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "guide.md").write_text("# Guide\n\n## Installation", encoding="utf-8")

        broken = validate_links_in_file(source, tmp_path)
        assert len(broken) == 1
        assert broken[0].error_type == "missing_file"
        assert "missing.md" in str(broken[0].resolved_path)
