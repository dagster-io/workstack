"""Unit tests for session-get-plan kit CLI command."""

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.data.kits.erk.kit_cli_commands.erk.session_get_plan import (
    PlanError,
    PlanResult,
    _extract_plan_filename,
    _find_session_file,
    _get_session_id_from_env,
    _is_excluded_pattern,
    _looks_like_uuid,
    find_plan_in_session,
    session_get_plan,
)


# ============================================================================
# 1. Helper Function Tests
# ============================================================================


def test_looks_like_uuid_valid() -> None:
    """Test UUID validation with valid UUID."""
    assert _looks_like_uuid("a02a1cae-b32a-41c1-a107-945ff5828724") is True


def test_looks_like_uuid_uppercase() -> None:
    """Test UUID validation rejects uppercase."""
    assert _looks_like_uuid("A02A1CAE-B32A-41C1-A107-945FF5828724") is False


def test_looks_like_uuid_invalid_format() -> None:
    """Test UUID validation with invalid format."""
    assert _looks_like_uuid("not-a-uuid") is False
    assert _looks_like_uuid("") is False
    assert _looks_like_uuid("12345") is False


def test_is_excluded_pattern_agent() -> None:
    """Test exclusion of agent log files."""
    assert _is_excluded_pattern("agent-abc123.md") is True


def test_is_excluded_pattern_temp() -> None:
    """Test exclusion of temp files."""
    assert _is_excluded_pattern("temp-plan.md") is True
    assert _is_excluded_pattern("tmp-draft.md") is True


def test_is_excluded_pattern_draft() -> None:
    """Test exclusion of draft files."""
    assert _is_excluded_pattern("draft-feature.md") is True


def test_is_excluded_pattern_valid() -> None:
    """Test non-excluded filenames pass through."""
    assert _is_excluded_pattern("ethereal-plotting-sunbeam.md") is False
    assert _is_excluded_pattern("feature-plan.md") is False
    assert _is_excluded_pattern("implementation-123.md") is False


def test_get_session_id_from_env_with_prefix(monkeypatch) -> None:
    """Test extracting session ID from SESSION_CONTEXT with 'session_id=' prefix."""
    monkeypatch.setenv("SESSION_CONTEXT", "session_id=abc-123-def-456")
    result = _get_session_id_from_env()
    assert result == "abc-123-def-456"


def test_get_session_id_from_env_bare_uuid(monkeypatch) -> None:
    """Test extracting bare UUID from SESSION_CONTEXT."""
    session_id = "a02a1cae-b32a-41c1-a107-945ff5828724"
    monkeypatch.setenv("SESSION_CONTEXT", session_id)
    result = _get_session_id_from_env()
    assert result == session_id


def test_get_session_id_from_env_missing(monkeypatch) -> None:
    """Test returns None when SESSION_CONTEXT not set."""
    monkeypatch.delenv("SESSION_CONTEXT", raising=False)
    result = _get_session_id_from_env()
    assert result is None


def test_get_session_id_from_env_invalid_format(monkeypatch) -> None:
    """Test returns None for invalid SESSION_CONTEXT format."""
    monkeypatch.setenv("SESSION_CONTEXT", "not-a-valid-format")
    result = _get_session_id_from_env()
    assert result is None


# ============================================================================
# 2. Session File Discovery Tests
# ============================================================================


def test_find_session_file_success(tmp_path: Path) -> None:
    """Test successful session file discovery."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()

    # Create project directory with session file
    project_dir = projects_dir / "project1"
    project_dir.mkdir()
    session_file = project_dir / "abc-123.jsonl"
    session_file.write_text("{}", encoding="utf-8")

    result = _find_session_file("abc-123", projects_dir)

    assert isinstance(result, Path)
    assert result == session_file


def test_find_session_file_multiple_projects(tmp_path: Path) -> None:
    """Test finding session file across multiple projects."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()

    # Create multiple project directories
    (projects_dir / "project1").mkdir()
    (projects_dir / "project1" / "session1.jsonl").write_text("{}", encoding="utf-8")

    project2 = projects_dir / "project2"
    project2.mkdir()
    session_file = project2 / "abc-123.jsonl"
    session_file.write_text("{}", encoding="utf-8")

    (projects_dir / "project3").mkdir()
    (projects_dir / "project3" / "session3.jsonl").write_text("{}", encoding="utf-8")

    result = _find_session_file("abc-123", projects_dir)

    assert isinstance(result, Path)
    assert result == session_file


def test_find_session_file_not_found(tmp_path: Path) -> None:
    """Test error when session file doesn't exist."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()

    result = _find_session_file("nonexistent", projects_dir)

    assert isinstance(result, PlanError)
    assert result.success is False
    assert result.error == "Session file not found"
    assert "nonexist" in result.help  # Session ID is truncated in help message


def test_find_session_file_projects_dir_missing(tmp_path: Path) -> None:
    """Test error when projects directory doesn't exist."""
    projects_dir = tmp_path / "nonexistent"

    result = _find_session_file("abc-123", projects_dir)

    assert isinstance(result, PlanError)
    assert result.success is False
    assert result.error == "Projects directory not found"


# ============================================================================
# 3. Plan Extraction Tests
# ============================================================================


def test_extract_plan_filename_success(tmp_path: Path) -> None:
    """Test successful plan extraction from session JSONL."""
    session_file = tmp_path / "session.jsonl"

    # Create JSONL with plan write
    content = json.dumps({
        "type": "user",
        "message": {
            "content": "cat > ~/.claude/plans/ethereal-plotting-sunbeam.md"
        }
    })
    session_file.write_text(content, encoding="utf-8")

    result = _extract_plan_filename(session_file)

    assert result == "ethereal-plotting-sunbeam.md"


def test_extract_plan_filename_with_hyphens_and_underscores(tmp_path: Path) -> None:
    """Test extraction supports hyphens, underscores, and numbers."""
    session_file = tmp_path / "session.jsonl"

    content = json.dumps({
        "type": "user",
        "message": {
            "content": "plans/feature_plan-123.md"
        }
    })
    session_file.write_text(content, encoding="utf-8")

    result = _extract_plan_filename(session_file)

    assert result == "feature_plan-123.md"


def test_extract_plan_filename_excludes_agent_logs(tmp_path: Path) -> None:
    """Test that agent logs are excluded from results."""
    session_file = tmp_path / "session.jsonl"

    # Create JSONL with agent log and real plan
    lines = [
        json.dumps({"type": "user", "message": {"content": "plans/agent-abc.md"}}),
        json.dumps({"type": "user", "message": {"content": "plans/real-plan.md"}})
    ]
    session_file.write_text("\n".join(lines), encoding="utf-8")

    result = _extract_plan_filename(session_file)

    assert result == "real-plan.md"


def test_extract_plan_filename_malformed_json_skipped(tmp_path: Path) -> None:
    """Test that malformed JSON lines are skipped gracefully."""
    session_file = tmp_path / "session.jsonl"

    lines = [
        "{ invalid json }",
        json.dumps({"type": "user", "message": {"content": "plans/valid-plan.md"}}),
        "another invalid line"
    ]
    session_file.write_text("\n".join(lines), encoding="utf-8")

    result = _extract_plan_filename(session_file)

    assert result == "valid-plan.md"


def test_extract_plan_filename_empty_lines_skipped(tmp_path: Path) -> None:
    """Test that empty lines are skipped."""
    session_file = tmp_path / "session.jsonl"

    lines = [
        "",
        json.dumps({"type": "user", "message": {"content": "plans/test-plan.md"}}),
        "",
        ""
    ]
    session_file.write_text("\n".join(lines), encoding="utf-8")

    result = _extract_plan_filename(session_file)

    assert result == "test-plan.md"


def test_extract_plan_filename_multiple_plans_returns_last(tmp_path: Path) -> None:
    """Test that most recent plan is returned when multiple exist."""
    session_file = tmp_path / "session.jsonl"

    lines = [
        json.dumps({"type": "user", "message": {"content": "plans/first-plan.md"}}),
        json.dumps({"type": "user", "message": {"content": "plans/second-plan.md"}}),
        json.dumps({"type": "user", "message": {"content": "plans/third-plan.md"}})
    ]
    session_file.write_text("\n".join(lines), encoding="utf-8")

    result = _extract_plan_filename(session_file)

    assert result == "third-plan.md"


def test_extract_plan_filename_no_plan_found(tmp_path: Path) -> None:
    """Test error when no plan exists in session."""
    session_file = tmp_path / "session.jsonl"

    content = json.dumps({
        "type": "user",
        "message": {"content": "some other content"}
    })
    session_file.write_text(content, encoding="utf-8")

    result = _extract_plan_filename(session_file)

    assert isinstance(result, PlanError)
    assert result.success is False
    assert result.error == "No plan file found in session"


def test_extract_plan_filename_unreadable_file(tmp_path: Path) -> None:
    """Test error when session file cannot be read."""
    session_file = tmp_path / "nonexistent.jsonl"

    result = _extract_plan_filename(session_file)

    assert isinstance(result, PlanError)
    assert result.success is False
    assert result.error == "Cannot read session file"


# ============================================================================
# 4. Integration Function Tests
# ============================================================================


def test_find_plan_in_session_success(tmp_path: Path, monkeypatch) -> None:
    """Test full workflow of finding plan from session."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()

    # Create project with session file
    project_dir = projects_dir / "project1"
    project_dir.mkdir()
    session_file = project_dir / "test-session.jsonl"

    content = json.dumps({
        "type": "user",
        "message": {"content": "plans/my-plan.md"}
    })
    session_file.write_text(content, encoding="utf-8")

    # Create the plan file
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    plan_file = plans_dir / "my-plan.md"
    plan_file.write_text("# Plan", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = find_plan_in_session("test-session", projects_dir)

    assert isinstance(result, PlanResult)
    assert result.success is True
    assert result.session_id == "test-session"
    assert result.plan_filename == "my-plan.md"
    assert result.plan_path == str(plan_file)
    assert result.warning is None


def test_find_plan_in_session_plan_file_deleted(tmp_path: Path, monkeypatch) -> None:
    """Test warning when plan file no longer exists."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()

    project_dir = projects_dir / "project1"
    project_dir.mkdir()
    session_file = project_dir / "test-session.jsonl"

    content = json.dumps({
        "type": "user",
        "message": {"content": "plans/deleted-plan.md"}
    })
    session_file.write_text(content, encoding="utf-8")

    # Don't create the plan file (simulating deletion)
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = find_plan_in_session("test-session", projects_dir)

    assert isinstance(result, PlanResult)
    assert result.success is True
    assert result.plan_filename == "deleted-plan.md"
    assert result.warning == "Plan file no longer exists"


def test_find_plan_in_session_session_not_found(tmp_path: Path) -> None:
    """Test error propagation when session file not found."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()

    result = find_plan_in_session("nonexistent", projects_dir)

    assert isinstance(result, PlanError)
    assert result.success is False
    assert result.error == "Session file not found"


def test_find_plan_in_session_no_plan_in_session(tmp_path: Path) -> None:
    """Test error propagation when no plan found."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()

    project_dir = projects_dir / "project1"
    project_dir.mkdir()
    session_file = project_dir / "test-session.jsonl"

    content = json.dumps({
        "type": "user",
        "message": {"content": "no plans here"}
    })
    session_file.write_text(content, encoding="utf-8")

    result = find_plan_in_session("test-session", projects_dir)

    assert isinstance(result, PlanError)
    assert result.success is False
    assert result.error == "No plan file found in session"


# ============================================================================
# 5. CLI Command Tests
# ============================================================================


def test_cli_success_with_session_id(tmp_path: Path, monkeypatch) -> None:
    """Test CLI with explicit session ID."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    project_dir = projects_dir / "project1"
    project_dir.mkdir()
    session_file = project_dir / "abc-123.jsonl"

    content = json.dumps({
        "type": "user",
        "message": {"content": "plans/test-plan.md"}
    })
    session_file.write_text(content, encoding="utf-8")

    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    (plans_dir / "test-plan.md").write_text("# Plan", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    runner = CliRunner()
    result = runner.invoke(session_get_plan, ["--session-id", "abc-123"])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["session_id"] == "abc-123"
    assert output["plan_filename"] == "test-plan.md"


def test_cli_success_from_environment(tmp_path: Path, monkeypatch) -> None:
    """Test CLI auto-detects session ID from environment."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    project_dir = projects_dir / "project1"
    project_dir.mkdir()
    session_file = project_dir / "env-session.jsonl"

    content = json.dumps({
        "type": "user",
        "message": {"content": "plans/env-plan.md"}
    })
    session_file.write_text(content, encoding="utf-8")

    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    (plans_dir / "env-plan.md").write_text("# Plan", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SESSION_CONTEXT", "session_id=env-session")

    runner = CliRunner()
    result = runner.invoke(session_get_plan, [])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["session_id"] == "env-session"


def test_cli_text_output_mode(tmp_path: Path, monkeypatch) -> None:
    """Test CLI with --text flag outputs plain filename."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    project_dir = projects_dir / "project1"
    project_dir.mkdir()
    session_file = project_dir / "abc-123.jsonl"

    content = json.dumps({
        "type": "user",
        "message": {"content": "plans/simple-plan.md"}
    })
    session_file.write_text(content, encoding="utf-8")

    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    (plans_dir / "simple-plan.md").write_text("# Plan", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    runner = CliRunner()
    result = runner.invoke(session_get_plan, ["--session-id", "abc-123", "--text"])

    assert result.exit_code == 0
    assert result.output.strip() == "simple-plan.md"


def test_cli_no_session_id_error(tmp_path: Path, monkeypatch) -> None:
    """Test CLI error when no session ID available."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("SESSION_CONTEXT", raising=False)

    runner = CliRunner()
    result = runner.invoke(session_get_plan, [])

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "No session ID provided"


def test_cli_session_not_found_error(tmp_path: Path, monkeypatch) -> None:
    """Test CLI error when session not found."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    runner = CliRunner()
    result = runner.invoke(session_get_plan, ["--session-id", "nonexistent"])

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "Session file not found"


def test_cli_json_output_structure_success(tmp_path: Path, monkeypatch) -> None:
    """Test JSON output has expected structure for success."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    project_dir = projects_dir / "project1"
    project_dir.mkdir()
    session_file = project_dir / "abc-123.jsonl"

    content = json.dumps({
        "type": "user",
        "message": {"content": "plans/test-plan.md"}
    })
    session_file.write_text(content, encoding="utf-8")

    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    (plans_dir / "test-plan.md").write_text("# Plan", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    runner = CliRunner()
    result = runner.invoke(session_get_plan, ["--session-id", "abc-123"])

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "session_id" in output
    assert "plan_filename" in output
    assert "plan_path" in output
    assert "warning" not in output  # No warning for valid plan

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["session_id"], str)
    assert isinstance(output["plan_filename"], str)
    assert isinstance(output["plan_path"], str)


def test_cli_json_output_structure_error(tmp_path: Path, monkeypatch) -> None:
    """Test JSON output has expected structure for error."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    runner = CliRunner()
    result = runner.invoke(session_get_plan, ["--session-id", "nonexistent"])

    assert result.exit_code == 1
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "error" in output
    assert "session_id" in output
    assert "help" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["error"], str)
    assert isinstance(output["session_id"], str)
    assert isinstance(output["help"], str)


def test_cli_warning_in_output(tmp_path: Path, monkeypatch) -> None:
    """Test warning appears in output when plan file deleted."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    project_dir = projects_dir / "project1"
    project_dir.mkdir()
    session_file = project_dir / "abc-123.jsonl"

    content = json.dumps({
        "type": "user",
        "message": {"content": "plans/deleted-plan.md"}
    })
    session_file.write_text(content, encoding="utf-8")

    # Create plans directory but not the plan file
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    runner = CliRunner()
    result = runner.invoke(session_get_plan, ["--session-id", "abc-123"])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["warning"] == "Plan file no longer exists"
