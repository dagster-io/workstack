"""Tests for artifact show and where commands."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from dot_agent_kit.cli import cli


def test_artifact_show_displays_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that artifact show displays artifact content."""
    # Set up artifact
    project_dir = tmp_path
    skills_dir = project_dir / ".claude" / "skills" / "test-skill"
    skills_dir.mkdir(parents=True)
    skill_content = "# Test Skill\n\nThis is a test skill."
    (skills_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")

    monkeypatch.chdir(project_dir)

    runner = CliRunner()
    result = runner.invoke(cli, ["artifact", "show", "test-skill"])

    assert result.exit_code == 0
    assert "test-skill" in result.output
    assert skill_content in result.output
    assert "Type:" in result.output
    assert "Level:" in result.output


def test_artifact_show_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that artifact show reports error for missing artifact."""
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["artifact", "show", "nonexistent"])

    assert result.exit_code == 1
    assert "No artifact found" in result.output


def test_artifact_show_with_type_filter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that artifact show respects type filter."""
    # Set up two artifacts with same name but different types
    project_dir = tmp_path
    claude_dir = project_dir / ".claude"

    # Create skill
    skill_dir = claude_dir / "skills" / "test"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Test Skill", encoding="utf-8")

    # Create command
    commands_dir = claude_dir / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "test.md").write_text("# Test Command", encoding="utf-8")

    monkeypatch.chdir(project_dir)

    runner = CliRunner()

    # Show skill
    result = runner.invoke(cli, ["artifact", "show", "test", "--type", "skill"])
    assert result.exit_code == 0
    assert "Test Skill" in result.output

    # Show command
    result = runner.invoke(cli, ["artifact", "show", "test", "--type", "command"])
    assert result.exit_code == 0
    assert "Test Command" in result.output


def test_artifact_show_ambiguous_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that artifact show reports error for ambiguous names."""
    # Set up two artifacts with same name
    project_dir = tmp_path
    claude_dir = project_dir / ".claude"

    # Create skill
    skill_dir = claude_dir / "skills" / "test"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Test Skill", encoding="utf-8")

    # Create command
    commands_dir = claude_dir / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "test.md").write_text("# Test Command", encoding="utf-8")

    monkeypatch.chdir(project_dir)

    runner = CliRunner()
    result = runner.invoke(cli, ["artifact", "show", "test"])

    assert result.exit_code == 1
    assert "Multiple artifacts found" in result.output
    assert "--type" in result.output


def test_artifact_where_shows_location(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that artifact where shows absolute path."""
    # Set up artifact
    project_dir = tmp_path
    skills_dir = project_dir / ".claude" / "skills" / "test-skill"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text("# Test Skill", encoding="utf-8")

    monkeypatch.chdir(project_dir)

    runner = CliRunner()
    result = runner.invoke(cli, ["artifact", "where", "test-skill"])

    assert result.exit_code == 0
    assert str(project_dir) in result.output
    assert ".claude" in result.output
    assert "skills" in result.output


def test_artifact_where_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that artifact where reports error for missing artifact."""
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["artifact", "where", "nonexistent"])

    assert result.exit_code == 1
    assert "No artifact found" in result.output


def test_artifact_where_multiple_locations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that artifact where shows all locations for duplicates."""
    # Set up artifact at both user and project level
    user_dir = tmp_path / "user"
    user_skills = user_dir / ".claude" / "skills" / "test-skill"
    user_skills.mkdir(parents=True)
    (user_skills / "SKILL.md").write_text("# User Skill", encoding="utf-8")

    project_dir = tmp_path / "project"
    project_skills = project_dir / ".claude" / "skills" / "test-skill"
    project_skills.mkdir(parents=True)
    (project_skills / "SKILL.md").write_text("# Project Skill", encoding="utf-8")

    monkeypatch.chdir(project_dir)
    monkeypatch.setenv("HOME", str(user_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["artifact", "where", "test-skill"])

    assert result.exit_code == 0
    assert "Multiple locations" in result.output
    assert "[user]" in result.output
    assert "[project]" in result.output
    assert str(user_dir) in result.output
    assert str(project_dir) in result.output


def test_artifact_where_with_type_filter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that artifact where respects type filter."""
    # Set up two artifacts with same name but different types
    project_dir = tmp_path
    claude_dir = project_dir / ".claude"

    # Create skill
    skill_dir = claude_dir / "skills" / "test"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Test Skill", encoding="utf-8")

    # Create command
    commands_dir = claude_dir / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "test.md").write_text("# Test Command", encoding="utf-8")

    monkeypatch.chdir(project_dir)

    runner = CliRunner()

    # Where for skill
    result = runner.invoke(cli, ["artifact", "where", "test", "--type", "skill"])
    assert result.exit_code == 0
    assert "skills" in result.output
    assert "commands" not in result.output

    # Where for command
    result = runner.invoke(cli, ["artifact", "where", "test", "--type", "command"])
    assert result.exit_code == 0
    assert "commands" in result.output
    assert "skills" not in result.output
