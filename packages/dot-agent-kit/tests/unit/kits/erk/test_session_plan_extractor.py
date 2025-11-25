"""Unit tests for session plan extraction functions.

Layer 3: Pure unit tests for isolated functions in session_plan_extractor.py
"""

import time
from pathlib import Path

from dot_agent_kit.data.kits.erk.session_plan_extractor import (
    get_latest_plan,
    get_plans_dir,
)
from tests.unit.kits.erk.fixtures import (
    SAMPLE_PLAN_CONTENT,
)

# ===============================================
# Tests for get_plans_dir()
# ===============================================


def test_get_plans_dir_returns_path() -> None:
    """Test that get_plans_dir returns a Path object."""
    result = get_plans_dir()
    assert isinstance(result, Path)


def test_get_plans_dir_has_correct_structure() -> None:
    """Test that get_plans_dir returns correct path structure."""
    result = get_plans_dir()
    assert result.parts[-2:] == (".claude", "plans")


def test_get_plans_dir_starts_with_home() -> None:
    """Test that plans dir starts with home directory."""
    result = get_plans_dir()
    assert str(result).startswith(str(Path.home()))


# ===============================================
# Tests for get_latest_plan()
# ===============================================


def test_get_latest_plan_returns_most_recent(monkeypatch, tmp_path: Path) -> None:
    """Test returns content of most recently modified plan file."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans directory
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    # Create older plan
    older_plan = plans_dir / "older-plan.md"
    older_plan.write_text("# Older Plan\nOld content", encoding="utf-8")

    # Ensure time difference
    time.sleep(0.01)

    # Create newer plan
    newer_plan = plans_dir / "newer-plan.md"
    newer_plan.write_text(SAMPLE_PLAN_CONTENT, encoding="utf-8")

    result = get_latest_plan("/any/working/dir")

    assert result == SAMPLE_PLAN_CONTENT


def test_get_latest_plan_nonexistent_plans_dir(monkeypatch, tmp_path: Path) -> None:
    """Test returns None when plans directory doesn't exist."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Don't create plans directory
    result = get_latest_plan("/any/working/dir")

    assert result is None


def test_get_latest_plan_empty_plans_dir(monkeypatch, tmp_path: Path) -> None:
    """Test returns None when plans directory is empty."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create empty plans directory
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    result = get_latest_plan("/any/working/dir")

    assert result is None


def test_get_latest_plan_single_plan(monkeypatch, tmp_path: Path) -> None:
    """Test returns content when only one plan exists."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans directory and single plan
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    plan_file = plans_dir / "only-plan.md"
    plan_file.write_text(SAMPLE_PLAN_CONTENT, encoding="utf-8")

    result = get_latest_plan("/any/working/dir")

    assert result == SAMPLE_PLAN_CONTENT


def test_get_latest_plan_ignores_non_md_files(monkeypatch, tmp_path: Path) -> None:
    """Test ignores non-.md files in plans directory."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans directory
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    # Create non-.md file (should be ignored)
    non_md = plans_dir / "notes.txt"
    non_md.write_text("This is not a plan", encoding="utf-8")

    # Ensure time difference
    time.sleep(0.01)

    # Create .md plan file
    plan_file = plans_dir / "real-plan.md"
    plan_file.write_text(SAMPLE_PLAN_CONTENT, encoding="utf-8")

    result = get_latest_plan("/any/working/dir")

    assert result == SAMPLE_PLAN_CONTENT


def test_get_latest_plan_ignores_directories(monkeypatch, tmp_path: Path) -> None:
    """Test ignores subdirectories in plans directory."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans directory
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    # Create a subdirectory (should be ignored)
    subdir = plans_dir / "archive"
    subdir.mkdir()

    # Create plan file
    plan_file = plans_dir / "current-plan.md"
    plan_file.write_text(SAMPLE_PLAN_CONTENT, encoding="utf-8")

    result = get_latest_plan("/any/working/dir")

    assert result == SAMPLE_PLAN_CONTENT


def test_get_latest_plan_parameters_unused(monkeypatch, tmp_path: Path) -> None:
    """Test that working_dir and session_id parameters don't affect result."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans directory and plan
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    plan_file = plans_dir / "test-plan.md"
    plan_file.write_text(SAMPLE_PLAN_CONTENT, encoding="utf-8")

    # Different working_dir and session_id should return same result
    result1 = get_latest_plan("/path/one")
    result2 = get_latest_plan("/path/two", session_id="session-123")
    result3 = get_latest_plan("/path/three", session_id="different-session")

    assert result1 == SAMPLE_PLAN_CONTENT
    assert result2 == SAMPLE_PLAN_CONTENT
    assert result3 == SAMPLE_PLAN_CONTENT
