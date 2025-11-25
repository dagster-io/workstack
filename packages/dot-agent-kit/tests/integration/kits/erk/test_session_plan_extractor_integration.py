"""Integration tests for plan extraction from ~/.claude/plans/.

Layer 4: Business logic tests using realistic file fixtures.
Tests the workflow of reading the most recent plan file.

Note: The plan-extractor agent (not this module) is responsible for
semantic validation that the plan matches conversation context.
"""

import time
from pathlib import Path

from dot_agent_kit.data.kits.erk.session_plan_extractor import (
    get_latest_plan,
)
from tests.unit.kits.erk.fixtures import (
    SAMPLE_PLAN_CONTENT,
)

# ===============================================
# Helpers
# ===============================================


def create_plan_file(mock_home: Path, slug: str, content: str) -> Path:
    """Create a plan file in the mock Claude plans directory.

    Args:
        mock_home: Mock home directory path
        slug: Plan slug (filename without .md)
        content: Plan content to write

    Returns:
        Path to created plan file
    """
    plans_dir = mock_home / ".claude" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    plan_file = plans_dir / f"{slug}.md"
    plan_file.write_text(content, encoding="utf-8")
    return plan_file


# ===============================================
# Integration Tests
# ===============================================


def test_full_workflow_returns_most_recent_plan(tmp_path: Path, monkeypatch) -> None:
    """Test complete workflow: read most recently modified plan file."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create older plan
    create_plan_file(tmp_path, "older-plan", "Old plan content")

    # Ensure time difference
    time.sleep(0.01)

    # Create newer plan
    create_plan_file(tmp_path, "newer-plan", SAMPLE_PLAN_CONTENT)

    # Should return newest plan
    result = get_latest_plan("/any/working/dir")

    assert result == SAMPLE_PLAN_CONTENT


def test_empty_plans_directory_returns_none(tmp_path: Path, monkeypatch) -> None:
    """Test that empty plans directory returns None."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create empty plans directory
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    result = get_latest_plan("/any/working/dir")

    assert result is None


def test_no_plans_directory_returns_none(tmp_path: Path, monkeypatch) -> None:
    """Test when plans directory doesn't exist."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Don't create any directories
    result = get_latest_plan("/any/working/dir")

    assert result is None


def test_single_plan_file(tmp_path: Path, monkeypatch) -> None:
    """Test with a single plan file."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create single plan
    create_plan_file(tmp_path, "only-plan", SAMPLE_PLAN_CONTENT)

    result = get_latest_plan("/any/working/dir")

    assert result == SAMPLE_PLAN_CONTENT


def test_multiple_plans_returns_most_recent(tmp_path: Path, monkeypatch) -> None:
    """Test that most recently modified plan is returned among many."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create several plans with time gaps
    for i in range(5):
        create_plan_file(tmp_path, f"plan-{i}", f"Plan {i} content")
        time.sleep(0.01)

    # Create the expected newest plan
    create_plan_file(tmp_path, "newest-plan", SAMPLE_PLAN_CONTENT)

    result = get_latest_plan("/any/working/dir")

    assert result == SAMPLE_PLAN_CONTENT


def test_ignores_non_markdown_files(tmp_path: Path, monkeypatch) -> None:
    """Test that non-.md files are ignored."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans directory
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    # Create various non-.md files
    (plans_dir / "notes.txt").write_text("Not a plan", encoding="utf-8")
    (plans_dir / "backup.json").write_text("{}", encoding="utf-8")
    (plans_dir / "README").write_text("Read me", encoding="utf-8")

    time.sleep(0.01)

    # Create actual plan file
    create_plan_file(tmp_path, "real-plan", SAMPLE_PLAN_CONTENT)

    result = get_latest_plan("/any/working/dir")

    assert result == SAMPLE_PLAN_CONTENT


def test_ignores_subdirectories(tmp_path: Path, monkeypatch) -> None:
    """Test that subdirectories are ignored even if named .md."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans directory
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    # Create a directory (not a file) with .md name
    fake_md_dir = plans_dir / "fake.md"
    fake_md_dir.mkdir()

    # Create actual plan file
    create_plan_file(tmp_path, "real-plan", SAMPLE_PLAN_CONTENT)

    result = get_latest_plan("/any/working/dir")

    assert result == SAMPLE_PLAN_CONTENT


def test_working_dir_parameter_ignored(tmp_path: Path, monkeypatch) -> None:
    """Test that working_dir parameter doesn't affect result."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    create_plan_file(tmp_path, "test-plan", SAMPLE_PLAN_CONTENT)

    # All different working dirs should return same result
    result1 = get_latest_plan("/path/one")
    result2 = get_latest_plan("/completely/different/path")
    result3 = get_latest_plan("/Users/someone/.erk/repos/project")

    assert result1 == SAMPLE_PLAN_CONTENT
    assert result2 == SAMPLE_PLAN_CONTENT
    assert result3 == SAMPLE_PLAN_CONTENT


def test_session_id_parameter_ignored(tmp_path: Path, monkeypatch) -> None:
    """Test that session_id parameter doesn't affect result."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    create_plan_file(tmp_path, "test-plan", SAMPLE_PLAN_CONTENT)

    # Different session IDs should return same result
    result1 = get_latest_plan("/path", session_id=None)
    result2 = get_latest_plan("/path", session_id="abc123")
    result3 = get_latest_plan("/path", session_id="different-session")

    assert result1 == SAMPLE_PLAN_CONTENT
    assert result2 == SAMPLE_PLAN_CONTENT
    assert result3 == SAMPLE_PLAN_CONTENT


def test_plan_with_unicode_content(tmp_path: Path, monkeypatch) -> None:
    """Test reading plan with unicode content."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    unicode_content = """# Plan with Unicode

- Emoji: 🚀 ✅ ❌
- Japanese: こんにちは
- Chinese: 你好
- Arabic: مرحبا
- Special: ñ ü ö ä
"""
    create_plan_file(tmp_path, "unicode-plan", unicode_content)

    result = get_latest_plan("/any/path")

    assert result == unicode_content


def test_plan_selection_by_mtime_not_name(tmp_path: Path, monkeypatch) -> None:
    """Test that selection is by modification time, not alphabetical order."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans with names that would sort differently than mtime
    create_plan_file(tmp_path, "zzz-oldest", "Oldest plan")
    time.sleep(0.01)
    create_plan_file(tmp_path, "aaa-newest", SAMPLE_PLAN_CONTENT)

    result = get_latest_plan("/path")

    # Should return "aaa-newest" because it's most recent, not "zzz-oldest"
    assert result == SAMPLE_PLAN_CONTENT
