"""Unit tests for agent_debug command.

Tests the agent-debug CLI command for inspecting failed agent runs.
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.agent_debug import (
    agent_debug,
    discover_agent_logs,
    export_json,
    find_project_dir_for_session,
    get_session_id_from_env,
    parse_agent_log,
)

# ============================================================================
# 1. Session ID Detection Tests
# ============================================================================


def test_get_session_id_from_env_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful session ID extraction from SESSION_CONTEXT env var."""
    monkeypatch.setenv("SESSION_CONTEXT", "session_id=abc123-def456")
    session_id = get_session_id_from_env()
    assert session_id == "abc123-def456"


def test_get_session_id_from_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test session ID extraction when SESSION_CONTEXT not set."""
    monkeypatch.delenv("SESSION_CONTEXT", raising=False)
    session_id = get_session_id_from_env()
    assert session_id is None


def test_get_session_id_from_env_invalid_format(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test session ID extraction with invalid format."""
    monkeypatch.setenv("SESSION_CONTEXT", "invalid_format")
    session_id = get_session_id_from_env()
    assert session_id is None


# ============================================================================
# 2. Agent Log Discovery Tests
# ============================================================================


def test_discover_agent_logs_finds_logs(tmp_path: Path) -> None:
    """Test discovering agent logs in directory."""
    # Create agent log files
    (tmp_path / "agent-123.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "agent-456.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "other.jsonl").write_text("", encoding="utf-8")

    logs = discover_agent_logs(tmp_path)

    assert len(logs) == 2
    assert all(log.stem.startswith("agent-") for log in logs)


def test_discover_agent_logs_empty_directory(tmp_path: Path) -> None:
    """Test discovering agent logs in empty directory."""
    logs = discover_agent_logs(tmp_path)
    assert logs == []


def test_discover_agent_logs_no_agent_files(tmp_path: Path) -> None:
    """Test discovering agent logs when no agent files exist."""
    (tmp_path / "session.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "other.log").write_text("", encoding="utf-8")

    logs = discover_agent_logs(tmp_path)
    assert logs == []


# ============================================================================
# 3. Project Directory Discovery Tests
# ============================================================================


def test_find_project_dir_for_session_success(tmp_path: Path) -> None:
    """Test finding project directory for a session ID."""
    # Create fake .claude/projects structure
    claude_dir = tmp_path / ".claude" / "projects"
    project_dir = claude_dir / "test-project"
    project_dir.mkdir(parents=True)

    # Create session log with session ID
    session_log = project_dir / "session.jsonl"
    session_entry = {"sessionId": "test-session-123", "type": "user", "message": {}}
    session_log.write_text(json.dumps(session_entry), encoding="utf-8")

    # Mock Path.home() to return tmp_path
    import dot_agent_kit.data.kits.erk.kit_cli_commands.erk.agent_debug as debug_module

    original_home = Path.home

    def mock_home() -> Path:
        return tmp_path

    debug_module.Path.home = staticmethod(mock_home)  # type: ignore

    try:
        found_dir = find_project_dir_for_session("test-session-123")
        assert found_dir == project_dir
    finally:
        debug_module.Path.home = staticmethod(original_home)  # type: ignore


def test_find_project_dir_for_session_not_found(tmp_path: Path) -> None:
    """Test finding project directory when session ID doesn't exist."""
    # Create fake .claude/projects structure
    claude_dir = tmp_path / ".claude" / "projects"
    claude_dir.mkdir(parents=True)

    # Mock Path.home() to return tmp_path
    import dot_agent_kit.data.kits.erk.kit_cli_commands.erk.agent_debug as debug_module

    original_home = Path.home

    def mock_home() -> Path:
        return tmp_path

    debug_module.Path.home = staticmethod(mock_home)  # type: ignore

    try:
        found_dir = find_project_dir_for_session("nonexistent-session")
        assert found_dir is None
    finally:
        debug_module.Path.home = staticmethod(original_home)  # type: ignore


# ============================================================================
# 4. Agent Log Parsing Tests
# ============================================================================


def test_parse_agent_log_success(tmp_path: Path) -> None:
    """Test parsing a successful agent log."""
    agent_log = tmp_path / "agent-abc123.jsonl"

    # Create log entries
    entries = [
        {
            "sessionId": "test-session",
            "type": "user",
            "message": {
                "content": [{"type": "text", "text": "Run pytest tests"}],
                "timestamp": 1700000000.0,
            },
        },
        {
            "sessionId": "test-session",
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "id": "tool1",
                        "input": {"command": "pytest"},
                    }
                ]
            },
        },
        {
            "sessionId": "test-session",
            "type": "tool_result",
            "message": {
                "tool_use_id": "tool1",
                "content": [{"type": "text", "text": "Exit code 0\nAll tests passed"}],
                "is_error": False,
            },
        },
    ]

    agent_log.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

    result = parse_agent_log(agent_log, "test-session")

    assert result["agent_id"] == "abc123"
    assert result["status"] == "success"
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["tool"] == "Bash"
    assert result["tool_calls"][0]["exit_code"] == 0


def test_parse_agent_log_with_failure(tmp_path: Path) -> None:
    """Test parsing an agent log with failures."""
    agent_log = tmp_path / "agent-def456.jsonl"

    entries = [
        {
            "sessionId": "test-session",
            "type": "user",
            "message": {
                "content": [{"type": "text", "text": "Build project"}],
                "timestamp": 1700000000.0,
            },
        },
        {
            "sessionId": "test-session",
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "id": "tool1",
                        "input": {"command": "make build"},
                    }
                ]
            },
        },
        {
            "sessionId": "test-session",
            "type": "tool_result",
            "message": {
                "tool_use_id": "tool1",
                "content": [{"type": "text", "text": "Exit code 2\nError: Build failed"}],
                "is_error": False,
            },
        },
    ]

    agent_log.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

    result = parse_agent_log(agent_log, "test-session")

    assert result["status"] == "failed"
    assert result["tool_calls"][0]["exit_code"] == 2
    assert result["tool_calls"][0]["error"] is not None


def test_parse_agent_log_filters_by_session(tmp_path: Path) -> None:
    """Test that parsing filters entries by session ID."""
    agent_log = tmp_path / "agent-xyz789.jsonl"

    entries = [
        {
            "sessionId": "other-session",
            "type": "user",
            "message": {"content": "Task from other session"},
        },
        {
            "sessionId": "test-session",
            "type": "user",
            "message": {
                "content": [{"type": "text", "text": "Task from test session"}],
                "timestamp": 1700000000.0,
            },
        },
    ]

    agent_log.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

    result = parse_agent_log(agent_log, "test-session")

    assert "test session" in result["task_description"]
    assert "other session" not in result["task_description"]


# ============================================================================
# 5. JSON Export Tests
# ============================================================================


def test_export_json_structure() -> None:
    """Test JSON export produces correct structure."""
    agents = [{"agent_id": "abc123", "agent_type": "devrun", "status": "failed", "tool_calls": []}]

    json_str = export_json(agents, "test-session")
    data = json.loads(json_str)

    assert data["session_id"] == "test-session"
    assert len(data["agents"]) == 1
    assert data["agents"][0]["agent_id"] == "abc123"


def test_export_json_multiple_agents() -> None:
    """Test JSON export with multiple agents."""
    agents = [
        {"agent_id": "agent1", "agent_type": "devrun", "status": "success", "tool_calls": []},
        {"agent_id": "agent2", "agent_type": "gt", "status": "failed", "tool_calls": []},
    ]

    json_str = export_json(agents, "test-session")
    data = json.loads(json_str)

    assert len(data["agents"]) == 2


# ============================================================================
# 6. CLI Integration Tests
# ============================================================================


def test_cli_missing_session_id() -> None:
    """Test CLI error when no session ID provided."""
    runner = CliRunner()
    result = runner.invoke(agent_debug, [])

    assert result.exit_code == 1
    assert "No session ID provided" in result.output


def test_cli_with_explicit_session_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test CLI with explicit --session-id flag."""
    # Create fake project structure
    claude_dir = tmp_path / ".claude" / "projects"
    project_dir = claude_dir / "test-project"
    project_dir.mkdir(parents=True)

    # Create session log
    session_log = project_dir / "session.jsonl"
    session_entry = {"sessionId": "test-123", "type": "user", "message": {}}
    session_log.write_text(json.dumps(session_entry), encoding="utf-8")

    # Create agent log
    agent_log = project_dir / "agent-abc.jsonl"
    agent_entries = [
        {
            "sessionId": "test-123",
            "type": "user",
            "message": {
                "content": [{"type": "text", "text": "Run task"}],
                "timestamp": 1700000000.0,
            },
        },
        {
            "sessionId": "test-123",
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "id": "t1",
                        "input": {"command": "echo test"},
                    }
                ]
            },
        },
        {
            "sessionId": "test-123",
            "type": "tool_result",
            "message": {
                "tool_use_id": "t1",
                "content": [{"type": "text", "text": "Exit code 1\nError"}],
                "is_error": False,
            },
        },
    ]
    agent_log.write_text("\n".join(json.dumps(e) for e in agent_entries), encoding="utf-8")

    # Mock Path.home()
    def mock_home() -> Path:
        return tmp_path

    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.agent_debug.Path.home",
        staticmethod(mock_home),
    )

    runner = CliRunner()
    result = runner.invoke(agent_debug, ["--session-id", "test-123"])

    assert result.exit_code == 0
    assert "Agent Runs for Session" in result.output


def test_cli_json_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test CLI with --json flag."""
    # Create fake project structure
    claude_dir = tmp_path / ".claude" / "projects"
    project_dir = claude_dir / "test-project"
    project_dir.mkdir(parents=True)

    # Create session log
    session_log = project_dir / "session.jsonl"
    session_entry = {"sessionId": "test-456", "type": "user", "message": {}}
    session_log.write_text(json.dumps(session_entry), encoding="utf-8")

    # Create agent log
    agent_log = project_dir / "agent-def.jsonl"
    agent_entries = [
        {
            "sessionId": "test-456",
            "type": "user",
            "message": {"content": [{"type": "text", "text": "Task"}], "timestamp": 1700000000.0},
        }
    ]
    agent_log.write_text("\n".join(json.dumps(e) for e in agent_entries), encoding="utf-8")

    # Mock Path.home()
    def mock_home() -> Path:
        return tmp_path

    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.agent_debug.Path.home",
        staticmethod(mock_home),
    )

    runner = CliRunner()
    result = runner.invoke(agent_debug, ["--session-id", "test-456", "--json", "--all"])

    assert result.exit_code == 0

    # Verify JSON output
    output_data = json.loads(result.output)
    assert output_data["session_id"] == "test-456"
    assert "agents" in output_data


def test_cli_filters_by_agent_type(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test CLI --agent-type filter."""
    # Create fake project structure
    claude_dir = tmp_path / ".claude" / "projects"
    project_dir = claude_dir / "test-project"
    project_dir.mkdir(parents=True)

    # Create session log
    session_log = project_dir / "session.jsonl"
    session_entry = {"sessionId": "test-789", "type": "user", "message": {}}
    session_log.write_text(json.dumps(session_entry), encoding="utf-8")

    # Create agent logs (one matching, one not)
    agent_log1 = project_dir / "agent-match.jsonl"
    agent_log1.write_text(
        json.dumps(
            {
                "sessionId": "test-789",
                "type": "user",
                "message": {
                    "content": [{"type": "text", "text": "subagent_type=devrun"}],
                    "timestamp": 1700000000.0,
                },
            }
        ),
        encoding="utf-8",
    )

    agent_log2 = project_dir / "agent-nomatch.jsonl"
    agent_log2.write_text(
        json.dumps(
            {
                "sessionId": "test-789",
                "type": "user",
                "message": {
                    "content": [{"type": "text", "text": "subagent_type=gt"}],
                    "timestamp": 1700000000.0,
                },
            }
        ),
        encoding="utf-8",
    )

    # Mock Path.home()
    def mock_home() -> Path:
        return tmp_path

    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.agent_debug.Path.home",
        staticmethod(mock_home),
    )

    runner = CliRunner()
    result = runner.invoke(
        agent_debug, ["--session-id", "test-789", "--agent-type", "devrun", "--json", "--all"]
    )

    assert result.exit_code == 0
    output_data = json.loads(result.output)
    assert len(output_data["agents"]) == 1
    assert output_data["agents"][0]["agent_type"] == "devrun"
