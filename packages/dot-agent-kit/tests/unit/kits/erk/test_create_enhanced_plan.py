"""Unit tests for create_enhanced_plan kit CLI command.

Tests all functions in create_enhanced_plan.py including discovery, assembly,
and CLI command entry points.
"""

import json
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_enhanced_plan import (
    AssembleResult,
    DiscoverError,
    DiscoverResult,
    _extract_title,
    _find_project_dir,
    _format_discovery_categories,
    _format_failed_attempts,
    _generate_filename,
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
# 2. Plan Parsing Tests (6 tests)
# ============================================================================


def test_extract_title_from_heading() -> None:
    """Test title extraction from markdown heading."""
    plan = "# My Implementation Plan\n\nSome content"
    assert _extract_title(cast(list[str], plan.splitlines())) == "My Implementation Plan"


def test_extract_title_with_extra_whitespace() -> None:
    """Test title extraction handles whitespace."""
    plan = "#   My Plan   \n\nContent"
    assert _extract_title(cast(list[str], plan.splitlines())) == "My Plan"


def test_extract_title_returns_default_if_no_heading() -> None:
    """Test default title when no heading found."""
    plan = "Some content without heading\n\nMore content"
    assert _extract_title(cast(list[str], plan.splitlines())) == "Implementation Plan"


def test_generate_filename_slugifies_title() -> None:
    """Test filename generation with slugification."""
    plan = "# Add New Feature for Users\n"
    filename = _generate_filename(cast(list[str], plan.splitlines()))
    assert filename == "add-new-feature-for-users-enhanced-plan.md"


def test_generate_filename_limits_to_30_chars() -> None:
    """Test filename truncation to 30 characters."""
    plan = "# This Is A Very Long Title That Exceeds Thirty Characters By A Lot\n"
    filename = _generate_filename(cast(list[str], plan.splitlines()))
    base = filename.replace("-enhanced-plan.md", "")
    assert len(base) <= 30


def test_generate_filename_removes_special_chars() -> None:
    """Test filename removes non-alphanumeric characters."""
    plan = "# Feature: Auth & Permissions!\n"
    filename = _generate_filename(cast(list[str], plan.splitlines()))
    # Should only contain alphanumeric and hyphens
    base = filename.replace("-enhanced-plan.md", "")
    assert all(c.isalnum() or c == "-" for c in base)


# ============================================================================
# 3. Discovery Formatting Tests (4 tests)
# ============================================================================


def test_format_discovery_categories_single_category() -> None:
    """Test formatting of single discovery category."""
    categories = {"API Discoveries": ["Found X pattern", "Learned Y behavior"]}
    result = _format_discovery_categories(categories)
    assert "#### API Discoveries" in result
    assert "- Found X pattern" in result
    assert "- Learned Y behavior" in result


def test_format_discovery_categories_multiple_categories() -> None:
    """Test formatting of multiple discovery categories."""
    categories = {
        "API Discoveries": ["Item 1"],
        "Architecture": ["Item 2", "Item 3"],
    }
    result = _format_discovery_categories(categories)
    assert "#### API Discoveries" in result
    assert "#### Architecture" in result
    assert "- Item 1" in result
    assert "- Item 2" in result


def test_format_failed_attempts_single_attempt() -> None:
    """Test formatting of single failed attempt."""
    attempts = [{"name": "Approach A", "reason": "Didn't work because X"}]
    result = _format_failed_attempts(attempts)
    assert "#### Failed Approaches Discovered" in result
    assert "**Approach A**: Didn't work because X" in result


def test_format_failed_attempts_multiple_attempts() -> None:
    """Test formatting of multiple failed attempts."""
    attempts = [
        {"name": "Approach A", "reason": "Reason A"},
        {"name": "Approach B", "reason": "Reason B"},
    ]
    result = _format_failed_attempts(attempts)
    assert "**Approach A**: Reason A" in result
    assert "**Approach B**: Reason B" in result


# ============================================================================
# 4. Execute Discover Tests (6 tests)
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
# 5. Execute Assemble Tests (5 tests)
# ============================================================================


def test_execute_assemble_success() -> None:
    """Test successful assemble phase execution."""
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
    assert "enriched_by_create_enhanced_plan: true" in result.content
    assert "API Discoveries" in result.content
    assert "Discovery 1" in result.content
    assert result.stats["discovery_count"] == 2


def test_execute_assemble_with_failed_attempts() -> None:
    """Test assemble includes failed attempts section."""
    plan_content = "# Test Plan\n\nContent"
    discoveries = {
        "session_id": "test",
        "categories": {},
        "failed_attempts": [{"name": "Approach A", "reason": "Didn't work"}],
        "raw_discoveries": [],
    }

    result = execute_assemble(plan_content, discoveries)

    assert isinstance(result, AssembleResult)
    assert result.success is True
    assert "What Didn't Work" in result.content
    assert "Approach A" in result.content


def test_execute_assemble_empty_discoveries() -> None:
    """Test assemble handles empty discoveries gracefully."""
    plan_content = "# Test Plan\n\nContent"
    discoveries = {
        "session_id": "test",
        "categories": {},
        "failed_attempts": [],
        "raw_discoveries": [],
    }

    result = execute_assemble(plan_content, discoveries)

    assert isinstance(result, AssembleResult)
    assert result.success is True
    assert "enriched_by_create_enhanced_plan: true" in result.content
    assert result.stats["discovery_count"] == 0


def test_execute_assemble_generates_valid_filename() -> None:
    """Test assemble generates valid filename."""
    plan_content = "# Add User Authentication\n\nContent"
    discoveries = {
        "session_id": "test",
        "categories": {},
        "failed_attempts": [],
        "raw_discoveries": [],
    }

    result = execute_assemble(plan_content, discoveries)

    assert isinstance(result, AssembleResult)
    assert result.success is True
    assert result.filename == "add-user-authentication-enhanced-plan.md"


def test_execute_assemble_includes_frontmatter() -> None:
    """Test assemble includes all required frontmatter fields."""
    plan_content = "# Test\n\nContent"
    discoveries = {
        "session_id": "abc-123",
        "categories": {},
        "failed_attempts": [],
        "raw_discoveries": ["A", "B"],
    }

    result = execute_assemble(plan_content, discoveries)

    assert isinstance(result, AssembleResult)
    assert result.success is True
    assert "session_id: abc-123" in result.content
    assert "discovery_count: 2" in result.content
    assert "timestamp:" in result.content


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
    """Test CLI assemble command execution."""
    runner = CliRunner()

    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Test Plan\n\n## Steps\n\n1. Do thing", encoding="utf-8")

    discoveries_file = tmp_path / "discoveries.json"
    discoveries_file.write_text(
        json.dumps(
            {
                "session_id": "test",
                "categories": {},
                "failed_attempts": [],
                "raw_discoveries": [],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        create_enhanced_plan,
        ["assemble", str(plan_file), str(discoveries_file)],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert "content" in output
    assert "filename" in output


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
