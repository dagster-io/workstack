"""Unit tests for session plan extraction functions.

Layer 3: Pure unit tests for isolated functions in session_plan_extractor.py
"""

import json
from pathlib import Path

from dot_agent_kit.data.kits.erk.session_plan_extractor import (
    construct_claude_project_name,
    get_claude_project_dir,
    get_latest_plan,
    get_plan_from_slug,
    get_plan_slug_from_session,
    get_plans_dir,
)
from tests.unit.kits.erk.fixtures import (
    JSONL_SESSION_WITH_SLUG,
    JSONL_SESSION_WITHOUT_SLUG,
    SAMPLE_PLAN_CONTENT,
    create_session_file,
)

# ===============================================
# Tests for construct_claude_project_name()
# ===============================================


def test_construct_claude_project_name_basic_path() -> None:
    """Test basic path without special characters."""
    result = construct_claude_project_name("/Users/schrockn/code/erk")
    assert result == "-Users-schrockn-code-erk"


def test_construct_claude_project_name_with_dots() -> None:
    """Test path with dots in directory names."""
    result = construct_claude_project_name("/Users/schrockn/.erk/repos/erk")
    assert result == "-Users-schrockn--erk-repos-erk"


def test_construct_claude_project_name_multiple_dots() -> None:
    """Test path with multiple dot directories."""
    result = construct_claude_project_name("/Users/schrockn/.config/.local/app")
    assert result == "-Users-schrockn--config--local-app"


def test_construct_claude_project_name_dotfile() -> None:
    """Test path ending with dotfile."""
    result = construct_claude_project_name("/Users/schrockn/.vimrc")
    assert result == "-Users-schrockn--vimrc"


def test_construct_claude_project_name_relative_path() -> None:
    """Test relative path (though should always be absolute in practice)."""
    result = construct_claude_project_name("./relative/path")
    # The leading dot gets replaced, then lstrip("-") removes all leading hyphens
    assert result == "-relative-path"


def test_construct_claude_project_name_root_path() -> None:
    """Test root directory path."""
    result = construct_claude_project_name("/")
    assert result == "-"


def test_construct_claude_project_name_worktree_path() -> None:
    """Test realistic worktree path (the actual bug case)."""
    result = construct_claude_project_name(
        "/Users/schrockn/.erk/repos/erk/worktrees/extract-from-session"
    )
    assert result == "-Users-schrockn--erk-repos-erk-worktrees-extract-from-session"


# ===============================================
# Tests for get_claude_project_dir()
# ===============================================


def test_get_claude_project_dir_basic_path() -> None:
    """Test basic directory path construction."""
    result = get_claude_project_dir("/Users/schrockn/code/erk")

    # Check that it returns a Path object
    assert isinstance(result, Path)

    # Check that it has correct structure (home / .claude / projects / project-name)
    assert result.parts[-3:] == (".claude", "projects", "-Users-schrockn-code-erk")


def test_get_claude_project_dir_with_dots() -> None:
    """Test directory path with dots."""
    result = get_claude_project_dir("/Users/schrockn/.erk/repos/erk")

    assert isinstance(result, Path)
    assert result.parts[-1] == "-Users-schrockn--erk-repos-erk"
    assert ".claude" in result.parts
    assert "projects" in result.parts


def test_get_claude_project_dir_ends_with_home() -> None:
    """Test that path starts with user's home directory."""
    result = get_claude_project_dir("/some/working/directory")

    # Should start with home directory
    assert str(result).startswith(str(Path.home()))


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
# Tests for get_plan_slug_from_session()
# ===============================================


def test_get_plan_slug_from_session_nonexistent_directory(tmp_path: Path) -> None:
    """Test returns None when project directory doesn't exist."""
    nonexistent = tmp_path / "nonexistent"
    result = get_plan_slug_from_session(nonexistent)

    assert result is None


def test_get_plan_slug_from_session_with_slug(tmp_path: Path) -> None:
    """Test extracts slug from session with slug field."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    session_file = project_dir / "session-123.jsonl"
    create_session_file(session_file, [JSONL_SESSION_WITH_SLUG])

    result = get_plan_slug_from_session(project_dir)

    assert result == "joyful-munching-hammock"


def test_get_plan_slug_from_session_without_slug(tmp_path: Path) -> None:
    """Test returns None when session has no slug field."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    session_file = project_dir / "session-123.jsonl"
    create_session_file(session_file, [JSONL_SESSION_WITHOUT_SLUG])

    result = get_plan_slug_from_session(project_dir)

    assert result is None


def test_get_plan_slug_from_session_first_slug_wins(tmp_path: Path) -> None:
    """Test returns first slug encountered (most recent file first)."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create first session with slug
    session1 = project_dir / "session-123.jsonl"
    create_session_file(session1, [JSONL_SESSION_WITH_SLUG])

    # Create second session entry with different slug
    session2 = project_dir / "session-456.jsonl"
    different_slug_entry = """{
      "type": "assistant",
      "slug": "different-slug-name",
      "message": {"role": "assistant", "content": []},
      "timestamp": "2025-11-23T12:00:00.000Z"
    }"""
    create_session_file(session2, [different_slug_entry])

    # Make session2 more recent
    import time

    time.sleep(0.01)
    session2.touch()

    result = get_plan_slug_from_session(project_dir)

    # Should return slug from most recently modified file
    assert result == "different-slug-name"


def test_get_plan_slug_from_session_filters_by_session_id(tmp_path: Path) -> None:
    """Test filters by specific session ID."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create session with slug
    session_file = project_dir / "target-session.jsonl"
    create_session_file(session_file, [JSONL_SESSION_WITH_SLUG])

    # Create another session without slug
    other_session = project_dir / "other-session.jsonl"
    create_session_file(other_session, [JSONL_SESSION_WITHOUT_SLUG])

    result = get_plan_slug_from_session(project_dir, session_id="target-session")

    assert result == "joyful-munching-hammock"


def test_get_plan_slug_from_session_nonexistent_session_id(tmp_path: Path) -> None:
    """Test returns None when specified session ID doesn't exist."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    session_file = project_dir / "session-123.jsonl"
    create_session_file(session_file, [JSONL_SESSION_WITH_SLUG])

    result = get_plan_slug_from_session(project_dir, session_id="nonexistent")

    assert result is None


def test_get_plan_slug_from_session_skips_malformed_json(tmp_path: Path) -> None:
    """Test gracefully handles malformed JSON lines."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    session_file = project_dir / "session-123.jsonl"
    with open(session_file, "w", encoding="utf-8") as f:
        # Write malformed JSON line
        f.write("not valid json\n")
        # Write valid entry with slug
        data = json.loads(JSONL_SESSION_WITH_SLUG)
        f.write(json.dumps(data) + "\n")

    result = get_plan_slug_from_session(project_dir)

    assert result == "joyful-munching-hammock"


def test_get_plan_slug_from_session_skips_empty_lines(tmp_path: Path) -> None:
    """Test skips empty lines in session file."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    session_file = project_dir / "session-123.jsonl"
    with open(session_file, "w", encoding="utf-8") as f:
        f.write("\n")  # Empty line
        f.write("   \n")  # Whitespace line
        data = json.loads(JSONL_SESSION_WITH_SLUG)
        f.write(json.dumps(data) + "\n")

    result = get_plan_slug_from_session(project_dir)

    assert result == "joyful-munching-hammock"


# ===============================================
# Tests for get_plan_from_slug()
# ===============================================


def test_get_plan_from_slug_existing_plan(monkeypatch, tmp_path: Path) -> None:
    """Test reads plan content from existing file."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans directory and plan file
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    plan_file = plans_dir / "test-slug.md"
    plan_file.write_text(SAMPLE_PLAN_CONTENT, encoding="utf-8")

    result = get_plan_from_slug("test-slug")

    assert result == SAMPLE_PLAN_CONTENT


def test_get_plan_from_slug_nonexistent_plan(monkeypatch, tmp_path: Path) -> None:
    """Test returns None when plan file doesn't exist."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create plans directory but no plan file
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    result = get_plan_from_slug("nonexistent-slug")

    assert result is None


def test_get_plan_from_slug_nonexistent_plans_dir(monkeypatch, tmp_path: Path) -> None:
    """Test returns None when plans directory doesn't exist."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Don't create plans directory
    result = get_plan_from_slug("any-slug")

    assert result is None


# ===============================================
# Tests for get_latest_plan()
# ===============================================


def test_get_latest_plan_full_integration(monkeypatch, tmp_path: Path) -> None:
    """Test full integration from working dir to plan extraction."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create Claude project directory structure
    working_dir = "/Users/schrockn/.erk/repos/erk"
    project_dir = tmp_path / ".claude" / "projects" / "-Users-schrockn--erk-repos-erk"
    project_dir.mkdir(parents=True)

    session_file = project_dir / "session-123.jsonl"
    create_session_file(session_file, [JSONL_SESSION_WITH_SLUG])

    # Create plans directory and plan file
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    plan_file = plans_dir / "joyful-munching-hammock.md"
    plan_file.write_text(SAMPLE_PLAN_CONTENT, encoding="utf-8")

    result = get_latest_plan(working_dir)

    assert result == SAMPLE_PLAN_CONTENT


def test_get_latest_plan_nonexistent_project(monkeypatch, tmp_path: Path) -> None:
    """Test returns None when project directory doesn't exist."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    working_dir = "/Users/schrockn/code/nonexistent"
    result = get_latest_plan(working_dir)

    assert result is None


def test_get_latest_plan_no_slug_in_session(monkeypatch, tmp_path: Path) -> None:
    """Test returns None when session has no slug field."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    working_dir = "/Users/schrockn/code/erk"
    project_dir = tmp_path / ".claude" / "projects" / "-Users-schrockn-code-erk"
    project_dir.mkdir(parents=True)

    session_file = project_dir / "session-123.jsonl"
    create_session_file(session_file, [JSONL_SESSION_WITHOUT_SLUG])

    result = get_latest_plan(working_dir)

    assert result is None


def test_get_latest_plan_slug_but_no_plan_file(monkeypatch, tmp_path: Path) -> None:
    """Test returns None when slug exists but plan file doesn't."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    working_dir = "/Users/schrockn/code/erk"
    project_dir = tmp_path / ".claude" / "projects" / "-Users-schrockn-code-erk"
    project_dir.mkdir(parents=True)

    session_file = project_dir / "session-123.jsonl"
    create_session_file(session_file, [JSONL_SESSION_WITH_SLUG])

    # Don't create plan file
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    result = get_latest_plan(working_dir)

    assert result is None


def test_get_latest_plan_with_session_id_filter(monkeypatch, tmp_path: Path) -> None:
    """Test session_id parameter filters correctly."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    working_dir = "/Users/schrockn/code/erk"
    project_dir = tmp_path / ".claude" / "projects" / "-Users-schrockn-code-erk"
    project_dir.mkdir(parents=True)

    # Create session with slug
    session_file = project_dir / "target-session.jsonl"
    create_session_file(session_file, [JSONL_SESSION_WITH_SLUG])

    # Create plans directory and plan file
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    plan_file = plans_dir / "joyful-munching-hammock.md"
    plan_file.write_text(SAMPLE_PLAN_CONTENT, encoding="utf-8")

    result = get_latest_plan(working_dir, session_id="target-session")

    assert result == SAMPLE_PLAN_CONTENT
