"""Tests for dot-agent md check command."""

import subprocess
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from dot_agent_kit.cli import cli


def test_check_passes_with_valid_files(tmp_path: Path) -> None:
    """Test check passes when CLAUDE.md files contain @AGENTS.md."""
    # Create a git repo
    (tmp_path / ".git").mkdir()

    # Create valid AGENTS.md + CLAUDE.md pair
    (tmp_path / "AGENTS.md").write_text("# Standards", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("@AGENTS.md", encoding="utf-8")

    # Mock git rev-parse to return tmp_path
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=0,
            stdout=str(tmp_path),
            stderr="",
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["md", "check"])

    assert result.exit_code == 0
    assert "✓ AGENTS.md standard: PASSED" in result.output
    assert "Files checked: 1" in result.output
    assert "Violations: 0" in result.output


def test_check_fails_missing_agents_md(tmp_path: Path) -> None:
    """Test check fails when CLAUDE.md exists without peer AGENTS.md."""
    # Create a git repo
    (tmp_path / ".git").mkdir()

    # Create CLAUDE.md without peer AGENTS.md
    (tmp_path / "CLAUDE.md").write_text("# Standards", encoding="utf-8")

    # Mock git rev-parse to return tmp_path
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=0,
            stdout=str(tmp_path),
            stderr="",
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["md", "check"])

    assert result.exit_code == 1
    assert "✗ AGENTS.md standard: FAILED" in result.output
    assert "Missing AGENTS.md:" in result.output
    assert "Found 1 violation" in result.output


def test_check_fails_invalid_claude_content(tmp_path: Path) -> None:
    """Test check fails when CLAUDE.md doesn't contain @AGENTS.md."""
    # Create a git repo
    (tmp_path / ".git").mkdir()

    # Create AGENTS.md and CLAUDE.md with wrong content
    (tmp_path / "AGENTS.md").write_text("# Standards", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("# Wrong content", encoding="utf-8")

    # Mock git rev-parse to return tmp_path
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=0,
            stdout=str(tmp_path),
            stderr="",
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["md", "check"])

    assert result.exit_code == 1
    assert "✗ AGENTS.md standard: FAILED" in result.output
    assert "Invalid CLAUDE.md content:" in result.output
    assert "expected '@AGENTS.md'" in result.output


def test_check_fails_multiple_violations(tmp_path: Path) -> None:
    """Test check reports multiple violations."""
    # Create a git repo
    (tmp_path / ".git").mkdir()

    # Create multiple issues
    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir1" / "CLAUDE.md").write_text("# No AGENTS.md", encoding="utf-8")

    (tmp_path / "dir2").mkdir()
    (tmp_path / "dir2" / "AGENTS.md").write_text("# Standards", encoding="utf-8")
    (tmp_path / "dir2" / "CLAUDE.md").write_text("# Wrong", encoding="utf-8")

    # Mock git rev-parse to return tmp_path
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=0,
            stdout=str(tmp_path),
            stderr="",
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["md", "check"])

    assert result.exit_code == 1
    assert "Found 2 violations" in result.output
    assert "Missing AGENTS.md:" in result.output
    assert "Invalid CLAUDE.md content:" in result.output


def test_check_no_claude_files(tmp_path: Path) -> None:
    """Test check passes when no CLAUDE.md files exist."""
    # Create a git repo
    (tmp_path / ".git").mkdir()

    # Mock git rev-parse to return tmp_path
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--show-toplevel"],
            returncode=0,
            stdout=str(tmp_path),
            stderr="",
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["md", "check"])

    assert result.exit_code == 0
    assert "No CLAUDE.md files found" in result.output


def test_check_cli_help() -> None:
    """Test check command help output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["md", "check", "--help"])

    assert result.exit_code == 0
    assert "Validate AGENTS.md standard compliance" in result.output
