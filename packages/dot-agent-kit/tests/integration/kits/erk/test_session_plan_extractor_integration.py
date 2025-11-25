"""Integration tests for session plan extraction with realistic session files.

Layer 4: Business logic tests using realistic file fixtures.
Tests the complete workflow of finding plans via slug field and plan files.
"""

import json
from pathlib import Path

from dot_agent_kit.data.kits.erk.session_plan_extractor import (
    get_claude_project_dir,
    get_latest_plan,
    get_plan_slug_from_session,
)
from tests.unit.kits.erk.fixtures import (
    JSONL_SESSION_WITH_SLUG,
    JSONL_SESSION_WITHOUT_SLUG,
    SAMPLE_PLAN_CONTENT,
)

# ===============================================
# Helpers
# ===============================================


def create_session_file(file_path: Path, *entries: str) -> None:
    """Create a JSONL session file with given entries.

    Args:
        file_path: Path to create file at
        entries: JSON strings to write (will be compacted to single lines)
    """
    # Ensure parent directory exists
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write entries as JSONL (one JSON object per line, no pretty printing)
    # Parse each entry and write as compact JSON to ensure single-line format
    with open(file_path, "w", encoding="utf-8") as f:
        for entry in entries:
            # Parse JSON and write back as compact single-line
            data = json.loads(entry)
            f.write(json.dumps(data) + "\n")


def create_mock_claude_project(tmp_path: Path, working_dir: str, monkeypatch) -> tuple[Path, Path]:
    """Create mock Claude project directory structure.

    Args:
        tmp_path: pytest tmp_path fixture
        working_dir: Working directory to encode
        monkeypatch: pytest monkeypatch fixture

    Returns:
        Tuple of (mock_home, project_dir)
    """
    # Mock home directory
    mock_home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: mock_home)

    # Get project directory using actual function
    project_dir = get_claude_project_dir(working_dir)

    # Create the directory structure
    if not project_dir.exists():
        project_dir.mkdir(parents=True, exist_ok=True)

    return mock_home, project_dir


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


def test_full_workflow_session_with_slug_and_plan(tmp_path: Path, monkeypatch) -> None:
    """Test complete workflow: session with slug → extract → read plan file."""
    working_dir = "/Users/schrockn/code/erk"
    mock_home, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Create session file with slug
    session_file = project_dir / "test-session-123.jsonl"
    create_session_file(session_file, JSONL_SESSION_WITH_SLUG)

    # Create matching plan file
    create_plan_file(mock_home, "joyful-munching-hammock", SAMPLE_PLAN_CONTENT)

    # Extract plan using full workflow
    result = get_latest_plan(working_dir)

    assert result == SAMPLE_PLAN_CONTENT


def test_session_without_slug_returns_none(tmp_path: Path, monkeypatch) -> None:
    """Test that session without slug field returns None."""
    working_dir = "/Users/schrockn/code/erk"
    mock_home, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Create session file without slug
    session_file = project_dir / "session.jsonl"
    create_session_file(session_file, JSONL_SESSION_WITHOUT_SLUG)

    # Even if plan file exists, should return None (no slug to find it)
    create_plan_file(mock_home, "joyful-munching-hammock", SAMPLE_PLAN_CONTENT)

    result = get_latest_plan(working_dir)

    assert result is None


def test_session_with_slug_but_no_plan_file(tmp_path: Path, monkeypatch) -> None:
    """Test that session with slug but missing plan file returns None."""
    working_dir = "/Users/schrockn/code/erk"
    _, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Create session file with slug
    session_file = project_dir / "session.jsonl"
    create_session_file(session_file, JSONL_SESSION_WITH_SLUG)

    # Don't create the plan file

    result = get_latest_plan(working_dir)

    assert result is None


def test_project_directory_not_found(tmp_path: Path, monkeypatch) -> None:
    """Test when project directory doesn't exist."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Don't create any directories
    result = get_latest_plan("/Users/schrockn/nonexistent/project")

    assert result is None


def test_slug_from_agent_file(tmp_path: Path, monkeypatch) -> None:
    """Test finding slug in an agent subprocess file (agent-*.jsonl)."""
    working_dir = "/Users/schrockn/code/erk"
    mock_home, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Create agent file with slug (not main session)
    agent_file = project_dir / "agent-abc123.jsonl"
    create_session_file(agent_file, JSONL_SESSION_WITH_SLUG)

    # Create matching plan file
    create_plan_file(mock_home, "joyful-munching-hammock", SAMPLE_PLAN_CONTENT)

    # Should find slug in agent file
    result = get_latest_plan(working_dir)

    assert result == SAMPLE_PLAN_CONTENT


def test_most_recent_session_file_wins(tmp_path: Path, monkeypatch) -> None:
    """Test that most recently modified session file is checked first."""
    working_dir = "/Users/schrockn/code/erk"
    mock_home, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Create older session with different slug
    older_entry = """{
        "type": "assistant",
        "slug": "older-slug-name",
        "message": {"role": "assistant", "content": []},
        "timestamp": "2025-11-23T10:00:00.000Z"
    }"""
    older_session = project_dir / "session-older.jsonl"
    create_session_file(older_session, older_entry)

    # Create newer session with different slug
    import time

    time.sleep(0.01)  # Ensure different mtime

    newer_entry = """{
        "type": "assistant",
        "slug": "newer-slug-name",
        "message": {"role": "assistant", "content": []},
        "timestamp": "2025-11-23T12:00:00.000Z"
    }"""
    newer_session = project_dir / "session-newer.jsonl"
    create_session_file(newer_session, newer_entry)

    # Create plan files for both
    create_plan_file(mock_home, "older-slug-name", "Old plan content")
    create_plan_file(mock_home, "newer-slug-name", "New plan content")

    # Should return plan from newer session file
    result = get_latest_plan(working_dir)

    assert result == "New plan content"


def test_session_id_filtering(tmp_path: Path, monkeypatch) -> None:
    """Test filtering by specific session ID."""
    working_dir = "/Users/schrockn/code/erk"
    mock_home, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Create target session with specific slug
    target_entry = """{
        "type": "assistant",
        "slug": "target-plan-slug",
        "message": {"role": "assistant", "content": []},
        "timestamp": "2025-11-23T10:00:00.000Z"
    }"""
    target_session = project_dir / "target-session.jsonl"
    create_session_file(target_session, target_entry)

    # Create other session with different slug (more recent)
    import time

    time.sleep(0.01)

    other_entry = """{
        "type": "assistant",
        "slug": "other-plan-slug",
        "message": {"role": "assistant", "content": []},
        "timestamp": "2025-11-23T12:00:00.000Z"
    }"""
    other_session = project_dir / "other-session.jsonl"
    create_session_file(other_session, other_entry)

    # Create plan files
    create_plan_file(mock_home, "target-plan-slug", "Target plan content")
    create_plan_file(mock_home, "other-plan-slug", "Other plan content")

    # Filter to target session
    result = get_latest_plan(working_dir, session_id="target-session")

    assert result == "Target plan content"


def test_malformed_json_handling(tmp_path: Path, monkeypatch) -> None:
    """Test graceful handling of malformed JSON lines."""
    working_dir = "/Users/schrockn/code/erk"
    mock_home, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Create file with malformed JSON and valid slug entry
    session_file = project_dir / "session.jsonl"
    with open(session_file, "w", encoding="utf-8") as f:
        # Write malformed JSON line
        f.write("{ this is not valid json }\n")
        # Write valid entry with slug
        data = json.loads(JSONL_SESSION_WITH_SLUG)
        f.write(json.dumps(data) + "\n")

    # Create matching plan file
    create_plan_file(mock_home, "joyful-munching-hammock", SAMPLE_PLAN_CONTENT)

    # Should skip malformed line and find the valid slug
    result = get_latest_plan(working_dir)

    assert result == SAMPLE_PLAN_CONTENT


def test_empty_session_files(tmp_path: Path, monkeypatch) -> None:
    """Test handling of empty session files."""
    working_dir = "/Users/schrockn/code/erk"
    _, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Create empty file
    session_file = project_dir / "empty.jsonl"
    session_file.touch()

    result = get_latest_plan(working_dir)

    assert result is None


def test_path_with_dots_integration(tmp_path: Path, monkeypatch) -> None:
    """Integration test for paths with dots."""
    working_dir = "/Users/schrockn/.erk/repos/erk"
    mock_home, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Verify project directory name has double hyphens for dots
    assert "--erk-repos-erk" in str(project_dir)

    # Create session file with slug
    session_file = project_dir / "test-session.jsonl"
    create_session_file(session_file, JSONL_SESSION_WITH_SLUG)

    # Create matching plan file
    create_plan_file(mock_home, "joyful-munching-hammock", SAMPLE_PLAN_CONTENT)

    # Extract plan using the full workflow
    result = get_latest_plan(working_dir)

    assert result == SAMPLE_PLAN_CONTENT


def test_multiple_dots_in_path_integration(tmp_path: Path, monkeypatch) -> None:
    """Integration test for paths with multiple dot directories."""
    working_dir = "/Users/schrockn/.config/.local/app"
    mock_home, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Verify dots are converted to hyphens
    assert "--config--local-app" in str(project_dir)

    # Create session file with slug
    session_file = project_dir / "session.jsonl"
    create_session_file(session_file, JSONL_SESSION_WITH_SLUG)

    # Create matching plan file
    create_plan_file(mock_home, "joyful-munching-hammock", SAMPLE_PLAN_CONTENT)

    # Extract plan
    result = get_latest_plan(working_dir)

    assert result == SAMPLE_PLAN_CONTENT


def test_worktree_path_integration(tmp_path: Path, monkeypatch) -> None:
    """Integration test with realistic worktree path (actual use case)."""
    working_dir = "/Users/schrockn/.erk/repos/erk/worktrees/extract-from-session"
    mock_home, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Verify project name is correct
    expected_name = "-Users-schrockn--erk-repos-erk-worktrees-extract-from-session"
    assert str(project_dir).endswith(expected_name)

    # Create session file with slug
    session_file = project_dir / "test-session.jsonl"
    create_session_file(session_file, JSONL_SESSION_WITH_SLUG)

    # Create matching plan file
    create_plan_file(mock_home, "joyful-munching-hammock", SAMPLE_PLAN_CONTENT)

    # Extract plan
    result = get_latest_plan(working_dir)

    assert result == SAMPLE_PLAN_CONTENT


def test_slug_appears_later_in_file(tmp_path: Path, monkeypatch) -> None:
    """Test finding slug that appears after other entries."""
    working_dir = "/Users/schrockn/code/erk"
    mock_home, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Create session with slug appearing after other entries
    session_file = project_dir / "session.jsonl"
    with open(session_file, "w", encoding="utf-8") as f:
        # First entries without slug
        f.write(json.dumps(json.loads(JSONL_SESSION_WITHOUT_SLUG)) + "\n")
        f.write(json.dumps(json.loads(JSONL_SESSION_WITHOUT_SLUG)) + "\n")
        # Then entry with slug
        f.write(json.dumps(json.loads(JSONL_SESSION_WITH_SLUG)) + "\n")

    # Create matching plan file
    create_plan_file(mock_home, "joyful-munching-hammock", SAMPLE_PLAN_CONTENT)

    # Should find the slug
    result = get_latest_plan(working_dir)

    assert result == SAMPLE_PLAN_CONTENT


def test_get_plan_slug_from_session_directly(tmp_path: Path, monkeypatch) -> None:
    """Test get_plan_slug_from_session function directly."""
    working_dir = "/Users/schrockn/code/erk"
    _, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Create session file with slug
    session_file = project_dir / "session.jsonl"
    create_session_file(session_file, JSONL_SESSION_WITH_SLUG)

    # Test direct slug extraction
    result = get_plan_slug_from_session(project_dir)

    assert result == "joyful-munching-hammock"
