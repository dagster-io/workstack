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
    assert "CLAUDE.md files checked: 1" in result.output
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
    assert "--check-links" in result.output


def test_check_ignores_broken_links_by_default(tmp_path: Path) -> None:
    """Test that broken @ references are ignored without --check-links flag."""
    # Create a git repo
    (tmp_path / ".git").mkdir()

    # Create .claude directory with broken @ reference
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "config.md").write_text("@nonexistent.md", encoding="utf-8")

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
        # Without --check-links, broken @ references should be ignored
        result = runner.invoke(cli, ["md", "check"])

    assert result.exit_code == 0
    assert "✓ AGENTS.md standard: PASSED" in result.output
    assert "Broken @ references" not in result.output


def test_check_passes_with_valid_at_references(tmp_path: Path) -> None:
    """Test check passes when @ references point to existing files."""
    # Create a git repo
    (tmp_path / ".git").mkdir()

    # Create .claude directory with valid @ references
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    skills_dir = claude_dir / "skills"
    skills_dir.mkdir()

    # Create target file
    (skills_dir / "my-skill.md").write_text("# My Skill\n\n## Setup", encoding="utf-8")

    # Create AGENTS.md with valid @ reference
    (tmp_path / "AGENTS.md").write_text(
        "# Standards\n\n@.claude/skills/my-skill.md", encoding="utf-8"
    )
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
        result = runner.invoke(cli, ["md", "check", "--check-links"])

    assert result.exit_code == 0
    assert "✓ AGENTS.md standard: PASSED" in result.output
    assert "All @ references are valid" in result.output


def test_check_fails_with_broken_at_reference(tmp_path: Path) -> None:
    """Test check fails when @ reference points to non-existent file."""
    # Create a git repo
    (tmp_path / ".git").mkdir()

    # Create .claude directory with broken @ reference
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    # Create file with broken @ reference (target doesn't exist)
    (claude_dir / "config.md").write_text("# Config\n\n@nonexistent.md", encoding="utf-8")

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
        result = runner.invoke(cli, ["md", "check", "--check-links"])

    assert result.exit_code == 1
    assert "✗ AGENTS.md standard: FAILED" in result.output
    assert "Broken @ references:" in result.output
    assert "File not found" in result.output
    assert "@nonexistent.md" in result.output


def test_check_fails_with_broken_fragment(tmp_path: Path) -> None:
    """Test check fails when @ reference has invalid fragment."""
    # Create a git repo
    (tmp_path / ".git").mkdir()

    # Create .claude directory
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    # Create target file without the referenced heading
    (claude_dir / "guide.md").write_text("# Guide\n\n## Introduction", encoding="utf-8")

    # Create file with @ reference to non-existent heading
    (claude_dir / "config.md").write_text(
        "# Config\n\n@guide.md#nonexistent-section", encoding="utf-8"
    )

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
        result = runner.invoke(cli, ["md", "check", "--check-links"])

    assert result.exit_code == 1
    assert "Broken @ references:" in result.output
    assert "Fragment not found" in result.output
    assert "#nonexistent-section" in result.output


def test_check_validates_claude_and_agent_dirs(tmp_path: Path) -> None:
    """Test check validates files in both .claude/ and .agent/ directories."""
    # Create a git repo
    (tmp_path / ".git").mkdir()

    # Create .claude directory with @ reference
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "file1.md").write_text("@missing1.md", encoding="utf-8")

    # Create .agent directory with @ reference
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir()
    (agent_dir / "file2.md").write_text("@missing2.md", encoding="utf-8")

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
        result = runner.invoke(cli, ["md", "check", "--check-links"])

    assert result.exit_code == 1
    assert "Broken @ references:" in result.output
    # Both missing references should be reported
    assert "@missing1.md" in result.output
    assert "@missing2.md" in result.output


def test_check_reports_file_and_fragment_errors(tmp_path: Path) -> None:
    """Test that both file and fragment errors are reported for same reference."""
    # Create a git repo
    (tmp_path / ".git").mkdir()

    # Create .claude directory
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    # Create file with @ reference to non-existent file with fragment
    (claude_dir / "config.md").write_text("# Config\n\n@nonexistent.md#section", encoding="utf-8")

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
        result = runner.invoke(cli, ["md", "check", "--check-links"])

    assert result.exit_code == 1
    assert "Broken @ references:" in result.output
    # Both errors should be reported
    assert "File not found" in result.output
    assert "Fragment not found" in result.output
