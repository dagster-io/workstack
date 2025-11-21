"""Unit tests for create_enhanced_plan kit CLI command.

Tests all functions in create_enhanced_plan.py including discovery, assembly,
and CLI command entry points.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_enhanced_plan import (
    AssembleResult,
    DiscoverError,
    DiscoverResult,
    _find_project_dir,
    _locate_session_log,
    _preprocess_logs,
    create_enhanced_plan,
    execute_assemble,
    execute_discover,
)

# ============================================================================
# 1. Project Discovery Tests (6 tests)
# ============================================================================


def test_find_project_dir_matches_cwd(tmp_path: Path, monkeypatch) -> None:
    """Test project directory discovery by cwd matching."""
    # Create mock ~/.claude/projects/ structure
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    # Create project directory with escaped path
    test_cwd = tmp_path / "test" / "repo"
    escaped_name = str(test_cwd).replace("/", "-")
    project_dir = projects_dir / escaped_name
    project_dir.mkdir()

    # Monkeypatch Path.home() to return tmp_path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Test discovery
    result = _find_project_dir(test_cwd)
    assert result == project_dir


def test_find_project_dir_returns_none_if_not_found(tmp_path: Path, monkeypatch) -> None:
    """Test graceful handling when project not found."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = _find_project_dir(tmp_path / "nonexistent")
    assert result is None


def test_find_project_dir_returns_none_if_projects_dir_missing(tmp_path: Path, monkeypatch) -> None:
    """Test graceful handling when ~/.claude/projects/ doesn't exist."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = _find_project_dir(tmp_path / "some" / "path")
    assert result is None


def test_find_project_dir_handles_dots_in_path(tmp_path: Path, monkeypatch) -> None:
    """Test that dots in paths are properly encoded (bug fix verification)."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    # Create path with hidden directory (contains dot)
    test_cwd = tmp_path / ".erk" / "repos" / "test"
    # Proper encoding: /tmp/.erk/repos/test → -tmp--erk-repos-test
    escaped_name = str(test_cwd).replace("/", "-").replace(".", "-")
    project_dir = projects_dir / escaped_name
    project_dir.mkdir()

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = _find_project_dir(test_cwd)
    assert result == project_dir


def test_locate_session_log_finds_jsonl_file(tmp_path: Path) -> None:
    """Test session log location."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    session_id = "test-session-123"
    log_file = project_dir / f"{session_id}.jsonl"
    log_file.write_text('{"test": "data"}', encoding="utf-8")

    result = _locate_session_log(project_dir, session_id)
    assert result == log_file


def test_locate_session_log_returns_none_if_not_found(tmp_path: Path) -> None:
    """Test graceful handling when session log not found."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = _locate_session_log(project_dir, "nonexistent-session")
    assert result is None


def test_locate_session_log_returns_none_if_project_dir_missing(tmp_path: Path) -> None:
    """Test graceful handling when project directory doesn't exist."""
    result = _locate_session_log(tmp_path / "nonexistent", "session-123")
    assert result is None


# ============================================================================
# 2. Execute Discover Tests (6 tests)
# ============================================================================


def test_execute_discover_success(tmp_path: Path, monkeypatch) -> None:
    """Test successful discovery phase execution."""
    # Set up mock project structure
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    cwd = tmp_path / "repo"
    project_dir = projects_dir / str(cwd).replace("/", "-")
    project_dir.mkdir()

    session_id = "test-123"
    log_file = project_dir / f"{session_id}.jsonl"
    log_file.write_text('{"type": "user", "message": {"content": "test"}}', encoding="utf-8")

    # Mock preprocessing to avoid complex setup
    mock_xml = "<session><user>test</user></session>"
    mock_stats = {
        "entries_processed": 1,
        "entries_skipped": 0,
        "token_reduction_pct": "50.0%",
        "original_size": 100,
        "compressed_size": 50,
    }

    with patch(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_enhanced_plan._preprocess_logs"
    ) as mock_preprocess:
        mock_preprocess.return_value = (mock_xml, mock_stats)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = execute_discover(session_id, cwd)

        assert isinstance(result, DiscoverResult)
        assert result.success is True
        assert result.compressed_xml == mock_xml
        assert result.stats == mock_stats
        assert result.session_id == session_id


def test_execute_discover_project_not_found(tmp_path: Path, monkeypatch) -> None:
    """Test error when project directory not found."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = execute_discover("test-session", tmp_path / "nonexistent")

    assert isinstance(result, DiscoverError)
    assert result.success is False
    assert result.error == "Project directory not found"
    assert "nonexistent" in result.help


def test_execute_discover_session_log_not_found(tmp_path: Path, monkeypatch) -> None:
    """Test error when session log not found."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    cwd = tmp_path / "repo"
    project_dir = projects_dir / str(cwd).replace("/", "-")
    project_dir.mkdir()

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = execute_discover("nonexistent-session", cwd)

    assert isinstance(result, DiscoverError)
    assert result.success is False
    assert result.error == "Session log not found"


def test_execute_discover_preprocessing_failed(tmp_path: Path, monkeypatch) -> None:
    """Test error when preprocessing fails."""
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    cwd = tmp_path / "repo"
    project_dir = projects_dir / str(cwd).replace("/", "-")
    project_dir.mkdir()

    session_id = "test-123"
    log_file = project_dir / f"{session_id}.jsonl"
    log_file.write_text('{"type": "user"}', encoding="utf-8")

    with patch(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_enhanced_plan._preprocess_logs"
    ) as mock_preprocess:
        mock_preprocess.side_effect = ValueError("Preprocessing error")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = execute_discover(session_id, cwd)

        assert isinstance(result, DiscoverError)
        assert result.success is False
        assert result.error == "Preprocessing failed"


def test_preprocess_logs_raises_on_missing_file(tmp_path: Path) -> None:
    """Test _preprocess_logs raises FileNotFoundError on missing file."""
    with pytest.raises(FileNotFoundError):
        _preprocess_logs(tmp_path / "nonexistent.jsonl", "session-123")


def test_preprocess_logs_raises_on_empty_session(tmp_path: Path) -> None:
    """Test _preprocess_logs raises ValueError on empty session."""
    log_file = tmp_path / "session.jsonl"
    log_file.write_text('{"type": "user", "message": {"content": ""}}', encoding="utf-8")

    with pytest.raises(ValueError, match="Empty session"):
        _preprocess_logs(log_file, "session-123")


# ============================================================================
# 5. Execute Assemble Tests (3 tests - infrastructure only, no text generation)
# ============================================================================


def test_execute_assemble_returns_inputs_for_llm() -> None:
    """Test assemble returns raw inputs for LLM composition (no text generation)."""
    plan_content = "# My Plan\n\n## Steps\n\n1. Do thing"
    discoveries = {
        "session_id": "test-123",
        "categories": {"API Discoveries": ["Found X pattern"]},
        "failed_attempts": [],
        "raw_discoveries": ["Discovery 1", "Discovery 2"],
    }

    result = execute_assemble(plan_content, discoveries)

    assert isinstance(result, AssembleResult)
    assert result.success is True
    assert result.plan_content == plan_content
    assert result.discoveries == discoveries


def test_execute_assemble_preserves_plan_content() -> None:
    """Test assemble preserves plan content exactly (no parsing or modification)."""
    plan_content = "# Test Plan\n\n## Section\n\nSome content with **formatting**"
    discoveries = {
        "session_id": "test",
        "categories": {},
        "failed_attempts": [],
        "raw_discoveries": [],
    }

    result = execute_assemble(plan_content, discoveries)

    assert isinstance(result, AssembleResult)
    assert result.plan_content == plan_content  # Exact match, no modifications


def test_execute_assemble_preserves_discoveries() -> None:
    """Test assemble preserves discoveries structure (no formatting)."""
    plan_content = "# Plan"
    discoveries = {
        "session_id": "test",
        "categories": {"Category A": ["Item 1", "Item 2"], "Category B": ["Item 3"]},
        "failed_attempts": [{"name": "Approach X", "reason": "Reason Y"}],
        "raw_discoveries": ["Raw 1", "Raw 2"],
    }

    result = execute_assemble(plan_content, discoveries)

    assert isinstance(result, AssembleResult)
    assert result.discoveries == discoveries  # Exact match, no modifications


# ============================================================================
# 6. CLI Command Tests (4 tests)
# ============================================================================


def test_cli_discover_command_success(tmp_path: Path, monkeypatch) -> None:
    """Test CLI discover command execution."""
    runner = CliRunner()

    # Set up test environment
    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    cwd = tmp_path / "repo"
    cwd.mkdir(parents=True)  # Create the cwd directory
    project_dir = projects_dir / str(cwd).replace("/", "-")
    project_dir.mkdir()

    session_id = "test-123"
    log_file = project_dir / f"{session_id}.jsonl"
    log_file.write_text('{"type": "user", "message": {"content": "test"}}', encoding="utf-8")

    # Mock preprocessing
    with patch(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_enhanced_plan._preprocess_logs"
    ) as mock:
        mock.return_value = ("<session></session>", {"entries_processed": 1})
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = runner.invoke(
            create_enhanced_plan,
            ["discover", "--session-id", session_id, "--cwd", str(cwd)],
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert "compressed_xml" in output


def test_cli_discover_command_error(tmp_path: Path, monkeypatch) -> None:
    """Test CLI discover command with error."""
    runner = CliRunner()

    projects_dir = tmp_path / ".claude" / "projects"
    projects_dir.mkdir(parents=True)

    # Create a cwd that exists but has no matching project
    cwd = tmp_path / "no-project-here"
    cwd.mkdir(parents=True)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = runner.invoke(
        create_enhanced_plan,
        ["discover", "--session-id", "test", "--cwd", str(cwd)],
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "Project directory not found"


def test_cli_assemble_command_success(tmp_path: Path) -> None:
    """Test CLI assemble command returns inputs for LLM composition."""
    runner = CliRunner()

    plan_content = "# Test Plan\n\n## Steps\n\n1. Do thing"
    plan_file = tmp_path / "plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    discoveries_data = {
        "session_id": "test",
        "categories": {},
        "failed_attempts": [],
        "raw_discoveries": [],
    }
    discoveries_file = tmp_path / "discoveries.json"
    discoveries_file.write_text(
        json.dumps(discoveries_data),
        encoding="utf-8",
    )

    result = runner.invoke(
        create_enhanced_plan,
        ["assemble", str(plan_file), str(discoveries_file)],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_content"] == plan_content
    assert output["discoveries"] == discoveries_data


def test_cli_assemble_command_with_malformed_json(tmp_path: Path) -> None:
    """Test CLI assemble command with malformed JSON."""
    runner = CliRunner()

    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Test\n", encoding="utf-8")

    discoveries_file = tmp_path / "discoveries.json"
    discoveries_file.write_text("invalid json", encoding="utf-8")

    result = runner.invoke(
        create_enhanced_plan,
        ["assemble", str(plan_file), str(discoveries_file)],
    )

    assert result.exit_code == 1
