"""Unit tests for session plan extraction functions.

Layer 3: Pure unit tests for isolated functions in session_plan_extractor.py
"""

import json
from pathlib import Path

from dot_agent_kit.data.kits.erk.session_plan_extractor import (
    construct_claude_project_name,
    extract_plan_from_session_line,
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
    JSONL_USER_MESSAGE_STRING,
    SESSION_AGENT_FILE_PLAN,
    SESSION_MULTIPLE_PLANS,
    SESSION_WITH_PLAN,
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
# Tests for extract_plan_from_session_line()
# ===============================================


def test_extract_plan_from_session_line_with_exit_plan_mode() -> None:
    """Test extracting plan from ExitPlanMode entry."""
    data = json.loads(JSONL_ASSISTANT_EXIT_PLAN_MODE)
    result = extract_plan_from_session_line(data)

    assert result == EXPECTED_PLAN_TEXT


def test_extract_plan_from_session_line_with_later_plan() -> None:
    """Test extracting plan from later timestamp entry."""
    data = json.loads(JSONL_ASSISTANT_EXIT_PLAN_MODE_LATER)
    result = extract_plan_from_session_line(data)

    assert result == EXPECTED_PLAN_TEXT_LATER


def test_extract_plan_from_session_line_with_earlier_plan() -> None:
    """Test extracting plan from earlier timestamp entry."""
    data = json.loads(JSONL_ASSISTANT_EXIT_PLAN_MODE_EARLIER)
    result = extract_plan_from_session_line(data)

    # Should still extract the plan (timestamp sorting happens at higher level)
    assert result is not None
    assert "Old Plan" in result


def test_extract_plan_from_session_line_no_exit_plan_mode() -> None:
    """Test with assistant message without ExitPlanMode."""
    data = json.loads(JSONL_ASSISTANT_TEXT)
    result = extract_plan_from_session_line(data)

    assert result is None


def test_extract_plan_from_session_line_missing_message() -> None:
    """Test with entry missing message field."""
    data = {"type": "assistant", "timestamp": "2025-11-23T10:00:00.000Z"}
    result = extract_plan_from_session_line(data)

    assert result is None


def test_extract_plan_from_session_line_missing_content() -> None:
    """Test with message missing content array."""
    data = {"type": "assistant", "message": {"role": "assistant"}}
    result = extract_plan_from_session_line(data)

    assert result is None


def test_extract_plan_from_session_line_non_list_content() -> None:
    """Test with content that is not a list."""
    data = {"type": "assistant", "message": {"role": "assistant", "content": "string content"}}
    result = extract_plan_from_session_line(data)

    assert result is None


def test_extract_plan_from_session_line_missing_input() -> None:
    """Test with ExitPlanMode missing input field."""
    data = {
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "name": "ExitPlanMode", "id": "tool123"}]},
    }
    result = extract_plan_from_session_line(data)

    assert result is None


def test_extract_plan_from_session_line_missing_plan_field() -> None:
    """Test with input missing plan field."""
    data = {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "tool_use", "name": "ExitPlanMode", "input": {"other_field": "value"}}
            ]
        },
    }
    result = extract_plan_from_session_line(data)

    assert result is None


def test_extract_plan_from_session_line_empty_plan() -> None:
    """Test with empty plan string."""
    data = {
        "type": "assistant",
        "message": {
            "content": [{"type": "tool_use", "name": "ExitPlanMode", "input": {"plan": ""}}]
        },
    }
    result = extract_plan_from_session_line(data)

    assert result is None


def test_extract_plan_from_session_line_non_string_plan() -> None:
    """Test with plan that is not a string."""
    data = {
        "type": "assistant",
        "message": {
            "content": [{"type": "tool_use", "name": "ExitPlanMode", "input": {"plan": 123}}]
        },
    }
    result = extract_plan_from_session_line(data)

    assert result is None


# ===============================================
# Tests for get_latest_plan_from_session()
# ===============================================


def test_get_latest_plan_from_session_nonexistent_directory(tmp_path: Path) -> None:
    """Test returns None when project directory doesn't exist."""
    nonexistent = tmp_path / "nonexistent"
    result = get_latest_plan_from_session(nonexistent)

    assert result is None


def test_get_latest_plan_from_session_single_session_file(tmp_path: Path) -> None:
    """Test extracts plan from a single session file."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    session_file = project_dir / "session-123.jsonl"
    create_session_file(session_file, SESSION_WITH_PLAN)

    result = get_latest_plan_from_session(project_dir)

    assert result == EXPECTED_PLAN_TEXT


def test_get_latest_plan_from_session_multiple_sessions(tmp_path: Path) -> None:
    """Test extracts most recent plan from multiple session files."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create two session files
    session1 = project_dir / "session-123.jsonl"
    create_session_file(session1, [JSONL_ASSISTANT_EXIT_PLAN_MODE_EARLIER])

    session2 = project_dir / "session-456.jsonl"
    create_session_file(session2, [JSONL_ASSISTANT_EXIT_PLAN_MODE_LATER])

    result = get_latest_plan_from_session(project_dir)

    # Should return the later plan based on timestamp
    assert result == EXPECTED_PLAN_TEXT_LATER


def test_get_latest_plan_from_session_agent_file(tmp_path: Path) -> None:
    """Test extracts plans from agent subprocess files."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    agent_file = project_dir / "agent-abc123.jsonl"
    create_session_file(agent_file, SESSION_AGENT_FILE_PLAN)

    result = get_latest_plan_from_session(project_dir)

    assert result == EXPECTED_PLAN_TEXT


def test_get_latest_plan_from_session_filters_by_session_id(tmp_path: Path) -> None:
    """Test filters plans by specific session ID."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create two sessions with different plans
    session1 = project_dir / "session-123.jsonl"
    create_session_file(session1, [JSONL_ASSISTANT_EXIT_PLAN_MODE])

    session2 = project_dir / "session-456.jsonl"
    create_session_file(session2, [JSONL_ASSISTANT_EXIT_PLAN_MODE_LATER])

    # Request specific session
    result = get_latest_plan_from_session(project_dir, session_id="session-456")

    assert result == EXPECTED_PLAN_TEXT_LATER


def test_get_latest_plan_from_session_no_plans_found(tmp_path: Path) -> None:
    """Test returns None when no plans exist in session files."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    session_file = project_dir / "session-123.jsonl"
    create_session_file(session_file, [JSONL_USER_MESSAGE_STRING, JSONL_ASSISTANT_TEXT])

    result = get_latest_plan_from_session(project_dir)

    assert result is None


def test_get_latest_plan_from_session_skips_malformed_json(tmp_path: Path) -> None:
    """Test gracefully handles malformed JSON lines."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    session_file = project_dir / "session-123.jsonl"
    with open(session_file, "w", encoding="utf-8") as f:
        # Write malformed JSON line
        f.write("not valid json\n")
        # Write valid plan as compact single-line JSON
        plan_data = json.loads(JSONL_ASSISTANT_EXIT_PLAN_MODE)
        f.write(json.dumps(plan_data) + "\n")
        # Write another malformed line
        f.write("{incomplete json\n")

    result = get_latest_plan_from_session(project_dir)

    # Should extract plan despite malformed lines
    assert result == EXPECTED_PLAN_TEXT


def test_get_latest_plan_from_session_multiple_plans_same_session(tmp_path: Path) -> None:
    """Test returns most recent when multiple plans in same session."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    session_file = project_dir / "session-123.jsonl"
    create_session_file(session_file, SESSION_MULTIPLE_PLANS)

    result = get_latest_plan_from_session(project_dir)

    # Should return the later plan
    assert result == EXPECTED_PLAN_TEXT_LATER


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
    create_session_file(session_file, SESSION_WITH_PLAN)

    result = get_latest_plan(working_dir)

    assert result == EXPECTED_PLAN_TEXT


def test_get_latest_plan_nonexistent_project(monkeypatch, tmp_path: Path) -> None:
    """Test returns None when project directory doesn't exist."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    working_dir = "/Users/schrockn/code/nonexistent"
    result = get_latest_plan(working_dir)

    assert result is None


def test_get_latest_plan_with_session_id_filter(monkeypatch, tmp_path: Path) -> None:
    """Test session_id parameter filters correctly."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    working_dir = "/Users/schrockn/code/erk"
    project_dir = tmp_path / ".claude" / "projects" / "-Users-schrockn-code-erk"
    project_dir.mkdir(parents=True)

    # Create two sessions
    session1 = project_dir / "session-123.jsonl"
    create_session_file(session1, [JSONL_ASSISTANT_EXIT_PLAN_MODE])

    session2 = project_dir / "session-456.jsonl"
    create_session_file(session2, [JSONL_ASSISTANT_EXIT_PLAN_MODE_LATER])

    result = get_latest_plan(working_dir, session_id="session-123")

    assert result == EXPECTED_PLAN_TEXT
