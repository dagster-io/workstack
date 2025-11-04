"""Tests for artifact list command."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from dot_agent_kit.cli import cli


def test_artifact_list_shows_no_artifacts_when_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that artifact list shows appropriate message when no artifacts exist."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["artifact", "list"])

    assert result.exit_code == 0
    assert "No artifacts found" in result.output


def test_artifact_list_shows_project_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that artifact list shows project-level artifacts."""
    # Set up project artifacts
    project_dir = tmp_path
    claude_dir = project_dir / ".claude"
    skills_dir = claude_dir / "skills" / "test-skill"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text("# Test Skill", encoding="utf-8")

    monkeypatch.chdir(project_dir)

    runner = CliRunner()
    result = runner.invoke(cli, ["artifact", "list"])

    assert result.exit_code == 0
    assert "test-skill" in result.output
    assert "[P]" in result.output  # Project level indicator


def test_artifact_list_user_filter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that --user filter shows only user-level artifacts."""
    # Set up user and project artifacts
    user_dir = tmp_path / "user"
    user_skills = user_dir / ".claude" / "skills" / "user-skill"
    user_skills.mkdir(parents=True)
    (user_skills / "SKILL.md").write_text("# User Skill", encoding="utf-8")

    project_dir = tmp_path / "project"
    project_skills = project_dir / ".claude" / "skills" / "project-skill"
    project_skills.mkdir(parents=True)
    (project_skills / "SKILL.md").write_text("# Project Skill", encoding="utf-8")

    monkeypatch.chdir(project_dir)
    monkeypatch.setenv("HOME", str(user_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["artifact", "list", "--user"])

    assert result.exit_code == 0
    assert "user-skill" in result.output
    assert "project-skill" not in result.output


def test_artifact_list_project_filter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that --project filter shows only project-level artifacts."""
    # Set up user and project artifacts
    user_dir = tmp_path / "user"
    user_skills = user_dir / ".claude" / "skills" / "user-skill"
    user_skills.mkdir(parents=True)
    (user_skills / "SKILL.md").write_text("# User Skill", encoding="utf-8")

    project_dir = tmp_path / "project"
    project_skills = project_dir / ".claude" / "skills" / "project-skill"
    project_skills.mkdir(parents=True)
    (project_skills / "SKILL.md").write_text("# Project Skill", encoding="utf-8")

    monkeypatch.chdir(project_dir)
    monkeypatch.setenv("HOME", str(user_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["artifact", "list", "--project"])

    assert result.exit_code == 0
    assert "project-skill" in result.output
    assert "user-skill" not in result.output


def test_artifact_list_type_filter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that --type filter works correctly."""
    # Set up different artifact types
    project_dir = tmp_path
    claude_dir = project_dir / ".claude"

    # Create skill
    skill_dir = claude_dir / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")

    # Create command
    commands_dir = claude_dir / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "test-command.md").write_text("# Command", encoding="utf-8")

    monkeypatch.chdir(project_dir)

    runner = CliRunner()

    # Test filtering by skill type
    result = runner.invoke(cli, ["artifact", "list", "--type", "skill"])
    assert result.exit_code == 0
    assert "test-skill" in result.output
    assert "test-command" not in result.output

    # Test filtering by command type
    result = runner.invoke(cli, ["artifact", "list", "--type", "command"])
    assert result.exit_code == 0
    assert "test-command" in result.output
    assert "test-skill" not in result.output


def test_artifact_list_verbose_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that --verbose shows detailed information."""
    # Set up artifact
    project_dir = tmp_path
    skills_dir = project_dir / ".claude" / "skills" / "test-skill"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text("# Test Skill", encoding="utf-8")

    monkeypatch.chdir(project_dir)

    runner = CliRunner()
    result = runner.invoke(cli, ["artifact", "list", "-v"])

    assert result.exit_code == 0
    assert "CLAUDE ARTIFACTS" in result.output
    assert "Path:" in result.output
    assert "Source:" in result.output


def test_artifact_list_shows_hooks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that artifact list shows hooks from settings."""
    # Set up project with hook
    project_dir = tmp_path
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir()

    # Create settings with hook
    settings_data = {
        "hooks": {
            "user-prompt-submit": [
                {
                    "matcher": "**",
                    "hooks": [{"command": "python3 .claude/hooks/test/hook.py"}],
                }
            ]
        }
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings_data), encoding="utf-8")

    # Create hook script
    hook_script = claude_dir / "hooks" / "test" / "hook.py"
    hook_script.parent.mkdir(parents=True)
    hook_script.write_text("# Test hook", encoding="utf-8")

    monkeypatch.chdir(project_dir)

    runner = CliRunner()
    result = runner.invoke(cli, ["artifact", "list"])

    assert result.exit_code == 0
    assert "Hooks" in result.output or "hooks" in result.output.lower()
