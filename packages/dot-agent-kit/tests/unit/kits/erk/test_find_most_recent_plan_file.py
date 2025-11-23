"""Unit tests for find_most_recent_plan_file kit CLI command.

Tests atomic discovery of *-plan.md files at repository root.
"""

import json
import time
from pathlib import Path

from click.testing import CliRunner

from erk.data.kits.erk.kit_cli_commands.erk.find_most_recent_plan_file import (
    PlanFileError,
    PlanFileSuccess,
    find_most_recent_plan_file,
    find_most_recent_plan_file_cli,
)

# ============================================================================
# 1. Success Case Tests (3 tests)
# ============================================================================


def test_find_single_plan_file(tmp_path: Path) -> None:
    """Test finding single plan file at repo root."""
    # Create single plan file
    plan_file = tmp_path / "my-feature-plan.md"
    plan_file.write_text("# Plan", encoding="utf-8")

    result = find_most_recent_plan_file(tmp_path)

    assert isinstance(result, PlanFileSuccess)
    assert result.success is True
    assert result.plan_file == str(plan_file)
    assert result.all_plan_files_count == 1
    assert result.modified_at.endswith("+00:00") or result.modified_at.endswith("Z")  # ISO format with UTC


def test_find_most_recent_among_multiple(tmp_path: Path) -> None:
    """Test selecting most recent when multiple plan files exist."""
    # Create multiple plan files with different modification times
    old_plan = tmp_path / "old-feature-plan.md"
    old_plan.write_text("# Old", encoding="utf-8")

    time.sleep(0.01)  # Ensure different timestamps

    recent_plan = tmp_path / "recent-feature-plan.md"
    recent_plan.write_text("# Recent", encoding="utf-8")

    result = find_most_recent_plan_file(tmp_path)

    assert isinstance(result, PlanFileSuccess)
    assert result.success is True
    assert result.plan_file == str(recent_plan)
    assert result.all_plan_files_count == 2


def test_find_plan_file_counts_all_plans(tmp_path: Path) -> None:
    """Test that all_plan_files_count includes all plan files."""
    # Create multiple plan files
    (tmp_path / "plan-a-plan.md").write_text("# A", encoding="utf-8")
    (tmp_path / "plan-b-plan.md").write_text("# B", encoding="utf-8")
    (tmp_path / "plan-c-plan.md").write_text("# C", encoding="utf-8")

    result = find_most_recent_plan_file(tmp_path)

    assert isinstance(result, PlanFileSuccess)
    assert result.all_plan_files_count == 3


# ============================================================================
# 2. Error Case Tests (4 tests)
# ============================================================================


def test_error_no_plan_files_found(tmp_path: Path) -> None:
    """Test error when no plan files exist at repo root."""
    # Create non-plan files
    (tmp_path / "README.md").write_text("# Readme", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("Notes", encoding="utf-8")

    result = find_most_recent_plan_file(tmp_path)

    assert isinstance(result, PlanFileError)
    assert result.success is False
    assert result.error == "no_plan_files_found"
    assert str(tmp_path) in result.message


def test_error_invalid_repo_root_not_exists(tmp_path: Path) -> None:
    """Test error when repo root doesn't exist."""
    nonexistent = tmp_path / "nonexistent"

    result = find_most_recent_plan_file(nonexistent)

    assert isinstance(result, PlanFileError)
    assert result.success is False
    assert result.error == "invalid_repo_root"
    assert "does not exist" in result.message


def test_error_invalid_repo_root_not_directory(tmp_path: Path) -> None:
    """Test error when repo root is a file, not directory."""
    # Create file instead of directory
    not_a_dir = tmp_path / "file.txt"
    not_a_dir.write_text("content", encoding="utf-8")

    result = find_most_recent_plan_file(not_a_dir)

    assert isinstance(result, PlanFileError)
    assert result.success is False
    assert result.error == "invalid_repo_root"
    assert "not a directory" in result.message


def test_error_empty_directory(tmp_path: Path) -> None:
    """Test error when directory is empty (no files at all)."""
    result = find_most_recent_plan_file(tmp_path)

    assert isinstance(result, PlanFileError)
    assert result.success is False
    assert result.error == "no_plan_files_found"


# ============================================================================
# 3. Edge Cases Tests (4 tests)
# ============================================================================


def test_ignores_plan_files_in_subdirectories(tmp_path: Path) -> None:
    """Test that plan files in subdirectories are ignored (maxdepth 1)."""
    # Create plan file at root
    root_plan = tmp_path / "root-plan.md"
    root_plan.write_text("# Root", encoding="utf-8")

    # Create plan file in subdirectory (should be ignored)
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "nested-plan.md").write_text("# Nested", encoding="utf-8")

    result = find_most_recent_plan_file(tmp_path)

    assert isinstance(result, PlanFileSuccess)
    assert result.plan_file == str(root_plan)
    assert result.all_plan_files_count == 1  # Only root plan counted


def test_ignores_files_not_matching_pattern(tmp_path: Path) -> None:
    """Test that only *-plan.md files are considered."""
    # Create plan file (should match)
    plan = tmp_path / "feature-plan.md"
    plan.write_text("# Plan", encoding="utf-8")

    # Create non-matching files
    (tmp_path / "plan.md").write_text("# Plan", encoding="utf-8")  # No dash
    (tmp_path / "feature-plan.txt").write_text("# Plan", encoding="utf-8")  # Wrong ext
    (tmp_path / "feature-Plan.md").write_text("# Plan", encoding="utf-8")  # Capital P

    result = find_most_recent_plan_file(tmp_path)

    assert isinstance(result, PlanFileSuccess)
    assert result.plan_file == str(plan)
    assert result.all_plan_files_count == 1


def test_handles_symlinks_correctly(tmp_path: Path) -> None:
    """Test that symlinks to plan files are handled correctly."""
    # Create real plan file
    real_plan = tmp_path / "real-feature-plan.md"
    real_plan.write_text("# Real", encoding="utf-8")

    # Create symlink to plan file
    link_plan = tmp_path / "link-feature-plan.md"
    link_plan.symlink_to(real_plan)

    result = find_most_recent_plan_file(tmp_path)

    # Both files should be counted (symlink is a file)
    assert isinstance(result, PlanFileSuccess)
    assert result.all_plan_files_count == 2


def test_modified_at_is_iso_format_utc(tmp_path: Path) -> None:
    """Test that modified_at is in ISO 8601 format with UTC timezone."""
    plan = tmp_path / "test-plan.md"
    plan.write_text("# Test", encoding="utf-8")

    result = find_most_recent_plan_file(tmp_path)

    assert isinstance(result, PlanFileSuccess)
    # ISO 8601 format check: YYYY-MM-DDTHH:MM:SS.microseconds+00:00 or Z
    assert "T" in result.modified_at
    assert result.modified_at.endswith("+00:00") or result.modified_at.endswith("Z")


# ============================================================================
# 4. CLI Command Tests (5 tests)
# ============================================================================


def test_cli_success_with_repo_root(tmp_path: Path) -> None:
    """Test CLI command with explicit --repo-root."""
    plan = tmp_path / "feature-plan.md"
    plan.write_text("# Feature", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(find_most_recent_plan_file_cli, ["--repo-root", str(tmp_path)])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_file"] == str(plan)


def test_cli_error_no_plan_files(tmp_path: Path) -> None:
    """Test CLI command error when no plan files found."""
    runner = CliRunner()
    result = runner.invoke(find_most_recent_plan_file_cli, ["--repo-root", str(tmp_path)])

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no_plan_files_found"


def test_cli_json_output_structure_success(tmp_path: Path) -> None:
    """Test CLI JSON output has expected structure for success."""
    plan = tmp_path / "test-plan.md"
    plan.write_text("# Test", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(find_most_recent_plan_file_cli, ["--repo-root", str(tmp_path)])

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "plan_file" in output
    assert "modified_at" in output
    assert "all_plan_files_count" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["plan_file"], str)
    assert isinstance(output["modified_at"], str)
    assert isinstance(output["all_plan_files_count"], int)


def test_cli_json_output_structure_error(tmp_path: Path) -> None:
    """Test CLI JSON output has expected structure for error."""
    runner = CliRunner()
    result = runner.invoke(find_most_recent_plan_file_cli, ["--repo-root", str(tmp_path)])

    assert result.exit_code == 1
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "error" in output
    assert "message" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["error"], str)
    assert isinstance(output["message"], str)


def test_cli_without_repo_root_uses_git(tmp_path: Path, monkeypatch) -> None:
    """Test CLI without --repo-root uses git rev-parse."""
    # Create a mock git repository
    git_root = tmp_path / "repo"
    git_root.mkdir()
    (git_root / ".git").mkdir()
    plan = git_root / "feature-plan.md"
    plan.write_text("# Feature", encoding="utf-8")

    # Mock subprocess to return git_root
    import subprocess

    original_run = subprocess.run

    def mock_run(cmd, **kwargs):
        if cmd == ["git", "rev-parse", "--show-toplevel"]:
            # Create mock result with required attributes
            result = type("Result", (), {"returncode": 0, "stdout": str(git_root)})()
            return result
        return original_run(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "run", mock_run)

    runner = CliRunner()
    result = runner.invoke(find_most_recent_plan_file_cli, [])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_file"] == str(plan)
