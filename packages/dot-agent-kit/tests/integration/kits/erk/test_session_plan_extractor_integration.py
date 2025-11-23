"""Integration tests for session plan extraction with realistic session files.

Layer 4: Business logic tests using realistic file fixtures.
Tests the complete workflow of finding and extracting plans from session files.
"""

import json
from pathlib import Path

from dot_agent_kit.data.kits.erk.session_plan_extractor import (
    get_claude_project_dir,
    get_latest_plan,
    get_latest_plan_from_session,
)
from tests.unit.kits.erk.fixtures import (
    EXPECTED_PLAN_TEXT,
    EXPECTED_PLAN_TEXT_LATER,
    JSONL_ASSISTANT_EXIT_PLAN_MODE,
    JSONL_ASSISTANT_EXIT_PLAN_MODE_EARLIER,
    JSONL_ASSISTANT_EXIT_PLAN_MODE_LATER,
    JSONL_ASSISTANT_TEXT,
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


# ===============================================
# Integration Tests
# ===============================================


def test_find_plan_in_main_session_file(tmp_path: Path, monkeypatch) -> None:
    """Test finding a plan in the main session file."""
    working_dir = "/Users/schrockn/code/erk"
    _, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Create session file with plan
    session_file = project_dir / "test-session-123.jsonl"
    create_session_file(session_file, JSONL_ASSISTANT_EXIT_PLAN_MODE)

    # Extract plan
    result = get_latest_plan_from_session(project_dir)

    assert result == EXPECTED_PLAN_TEXT


def test_find_plan_in_agent_file(tmp_path: Path, monkeypatch) -> None:
    """Test finding a plan in an agent subprocess file (agent-*.jsonl)."""
    working_dir = "/Users/schrockn/code/erk"
    _, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Create agent file with plan
    agent_file = project_dir / "agent-abc123.jsonl"
    create_session_file(agent_file, JSONL_ASSISTANT_EXIT_PLAN_MODE)

    # Extract plan - should find it in agent file
    result = get_latest_plan_from_session(project_dir)

    assert result == EXPECTED_PLAN_TEXT


def test_find_latest_plan_with_timestamp_sorting(tmp_path: Path, monkeypatch) -> None:
    """Test that latest plan by timestamp is returned when multiple plans exist."""
    working_dir = "/Users/schrockn/code/erk"
    _, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Create multiple session files with different timestamps
    session1 = project_dir / "session-1.jsonl"
    create_session_file(session1, JSONL_ASSISTANT_EXIT_PLAN_MODE_EARLIER)

    session2 = project_dir / "session-2.jsonl"
    create_session_file(session2, JSONL_ASSISTANT_EXIT_PLAN_MODE_LATER)

    session3 = project_dir / "session-3.jsonl"
    create_session_file(session3, JSONL_ASSISTANT_EXIT_PLAN_MODE)

    # Should return the latest plan (from LATER fixture)
    result = get_latest_plan_from_session(project_dir)

    assert result == EXPECTED_PLAN_TEXT_LATER


def test_find_plan_across_main_and_agent_files(tmp_path: Path, monkeypatch) -> None:
    """Test finding plans across both main and agent files."""
    working_dir = "/Users/schrockn/code/erk"
    _, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Create main session with older plan
    main_session = project_dir / "main-session.jsonl"
    create_session_file(main_session, JSONL_ASSISTANT_EXIT_PLAN_MODE_EARLIER)

    # Create agent file with newer plan
    agent_file = project_dir / "agent-xyz789.jsonl"
    create_session_file(agent_file, JSONL_ASSISTANT_EXIT_PLAN_MODE_LATER)

    # Should return the newer plan from agent file
    result = get_latest_plan_from_session(project_dir)

    assert result == EXPECTED_PLAN_TEXT_LATER


def test_no_plan_found_in_session_files(tmp_path: Path, monkeypatch) -> None:
    """Test when no plan exists in any session file."""
    working_dir = "/Users/schrockn/code/erk"
    _, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Create session file without plan
    session_file = project_dir / "session.jsonl"
    create_session_file(session_file, JSONL_ASSISTANT_TEXT)

    # Should return None
    result = get_latest_plan_from_session(project_dir)

    assert result is None


def test_project_directory_not_found(tmp_path: Path) -> None:
    """Test when project directory doesn't exist."""
    non_existent_dir = tmp_path / "does-not-exist"

    result = get_latest_plan_from_session(non_existent_dir)

    assert result is None


def test_session_id_filtering(tmp_path: Path, monkeypatch) -> None:
    """Test filtering by specific session ID."""
    working_dir = "/Users/schrockn/code/erk"
    _, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Create multiple session files
    session1 = project_dir / "session-target.jsonl"
    create_session_file(session1, JSONL_ASSISTANT_EXIT_PLAN_MODE)

    session2 = project_dir / "session-other.jsonl"
    create_session_file(session2, JSONL_ASSISTANT_EXIT_PLAN_MODE_LATER)

    # Filter to specific session
    result = get_latest_plan_from_session(project_dir, session_id="session-target")

    # Should return plan from target session, not the other one
    assert result == EXPECTED_PLAN_TEXT


def test_malformed_json_handling(tmp_path: Path, monkeypatch) -> None:
    """Test graceful handling of malformed JSON lines."""
    working_dir = "/Users/schrockn/code/erk"
    _, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Create file with malformed JSON and valid plan
    # Write directly to file (not using create_session_file) to test malformed JSON handling
    session_file = project_dir / "session.jsonl"
    with open(session_file, "w", encoding="utf-8") as f:
        # Write malformed JSON line
        f.write("{ this is not valid json }\n")
        # Write valid plan as compact single-line JSON
        plan_data = json.loads(JSONL_ASSISTANT_EXIT_PLAN_MODE)
        f.write(json.dumps(plan_data) + "\n")

    # Should skip malformed line and find the valid plan
    result = get_latest_plan_from_session(project_dir)

    assert result == EXPECTED_PLAN_TEXT


def test_empty_session_files(tmp_path: Path, monkeypatch) -> None:
    """Test handling of empty session files."""
    working_dir = "/Users/schrockn/code/erk"
    _, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Create empty file
    session_file = project_dir / "empty.jsonl"
    session_file.touch()

    # Should return None
    result = get_latest_plan_from_session(project_dir)

    assert result is None


def test_path_with_dots_integration(tmp_path: Path, monkeypatch) -> None:
    """Integration test for paths with dots (the bug we're fixing)."""
    working_dir = "/Users/schrockn/.erk/repos/erk"
    _, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Verify project directory name has double hyphens for dots
    assert "--erk-repos-erk" in str(project_dir)

    # Create session file with plan
    session_file = project_dir / "test-session.jsonl"
    create_session_file(session_file, JSONL_ASSISTANT_EXIT_PLAN_MODE)

    # Extract plan using the full workflow
    result = get_latest_plan(working_dir)

    assert result == EXPECTED_PLAN_TEXT


def test_multiple_dots_in_path_integration(tmp_path: Path, monkeypatch) -> None:
    """Integration test for paths with multiple dot directories."""
    working_dir = "/Users/schrockn/.config/.local/app"
    _, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Verify dots are converted to hyphens
    assert "--config--local-app" in str(project_dir)

    # Create session file with plan
    session_file = project_dir / "session.jsonl"
    create_session_file(session_file, JSONL_ASSISTANT_EXIT_PLAN_MODE)

    # Extract plan
    result = get_latest_plan(working_dir)

    assert result == EXPECTED_PLAN_TEXT


def test_worktree_path_integration(tmp_path: Path, monkeypatch) -> None:
    """Integration test with realistic worktree path (actual use case)."""
    working_dir = "/Users/schrockn/.erk/repos/erk/worktrees/extract-from-session"
    _, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Verify project name is correct
    expected_name = "-Users-schrockn--erk-repos-erk-worktrees-extract-from-session"
    assert str(project_dir).endswith(expected_name)

    # Create session file with plan
    session_file = project_dir / "test-session.jsonl"
    create_session_file(session_file, JSONL_ASSISTANT_EXIT_PLAN_MODE)

    # Extract plan
    result = get_latest_plan(working_dir)

    assert result == EXPECTED_PLAN_TEXT


def test_multiple_plans_in_same_file(tmp_path: Path, monkeypatch) -> None:
    """Test multiple ExitPlanMode entries in a single session file."""
    working_dir = "/Users/schrockn/code/erk"
    _, project_dir = create_mock_claude_project(tmp_path, working_dir, monkeypatch)

    # Create file with multiple plans (different timestamps)
    session_file = project_dir / "session.jsonl"
    create_session_file(
        session_file,
        JSONL_ASSISTANT_EXIT_PLAN_MODE_EARLIER,
        JSONL_ASSISTANT_EXIT_PLAN_MODE,
        JSONL_ASSISTANT_EXIT_PLAN_MODE_LATER,
    )

    # Should return the latest one
    result = get_latest_plan_from_session(project_dir)

    assert result == EXPECTED_PLAN_TEXT_LATER
