"""Tests for unified artifact discovery service."""

import json
from pathlib import Path

from dot_agent_kit.models.artifact import ArtifactLevel, ArtifactSource
from dot_agent_kit.services.unified_discovery import UnifiedArtifactDiscovery


def test_discovers_artifacts_from_both_levels(tmp_path: Path) -> None:
    """Test that service discovers artifacts from both user and project levels."""
    # Set up user-level artifacts
    user_dir = tmp_path / "user"
    user_claude = user_dir / ".claude"
    user_skills = user_claude / "skills" / "user-skill"
    user_skills.mkdir(parents=True)
    (user_skills / "SKILL.md").write_text("# User Skill", encoding="utf-8")

    # Set up project-level artifacts
    project_dir = tmp_path / "project"
    project_claude = project_dir / ".claude"
    project_skills = project_claude / "skills" / "project-skill"
    project_skills.mkdir(parents=True)
    (project_skills / "SKILL.md").write_text("# Project Skill", encoding="utf-8")

    # Discover artifacts
    discovery = UnifiedArtifactDiscovery()
    result = discovery.discover_all(project_dir=project_dir, user_home=user_dir)

    # Should find artifacts at both levels
    assert len(result.user_artifacts) == 1
    assert len(result.project_artifacts) == 1

    # Verify levels are correct
    assert result.user_artifacts[0].level == ArtifactLevel.USER
    assert result.project_artifacts[0].level == ArtifactLevel.PROJECT

    # Verify names
    assert result.user_artifacts[0].artifact_name == "user-skill"
    assert result.project_artifacts[0].artifact_name == "project-skill"


def test_all_artifacts_combines_both_levels(tmp_path: Path) -> None:
    """Test that all_artifacts() combines user and project artifacts."""
    # Set up artifacts
    user_dir = tmp_path / "user"
    project_dir = tmp_path / "project"

    # User skill
    user_skills = user_dir / ".claude" / "skills" / "skill1"
    user_skills.mkdir(parents=True)
    (user_skills / "SKILL.md").write_text("# Skill 1", encoding="utf-8")

    # Project skill
    project_skills = project_dir / ".claude" / "skills" / "skill2"
    project_skills.mkdir(parents=True)
    (project_skills / "SKILL.md").write_text("# Skill 2", encoding="utf-8")

    discovery = UnifiedArtifactDiscovery()
    result = discovery.discover_all(project_dir=project_dir, user_home=user_dir)

    all_artifacts = result.all_artifacts()
    assert len(all_artifacts) == 2

    # Should have one from each level
    levels = {a.level for a in all_artifacts}
    assert levels == {ArtifactLevel.USER, ArtifactLevel.PROJECT}


def test_filter_by_type(tmp_path: Path) -> None:
    """Test filtering artifacts by type."""
    project_dir = tmp_path / "project"
    project_claude = project_dir / ".claude"

    # Create skill
    skill_dir = project_claude / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")

    # Create command
    commands_dir = project_claude / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "test-command.md").write_text("# Command", encoding="utf-8")

    discovery = UnifiedArtifactDiscovery()
    result = discovery.discover_all(project_dir=project_dir, user_home=tmp_path / "user")

    # Filter by skill type
    skills_only = result.filter_by_type("skill")
    assert len(skills_only.all_artifacts()) == 1
    assert skills_only.all_artifacts()[0].artifact_type == "skill"

    # Filter by command type
    commands_only = result.filter_by_type("command")
    assert len(commands_only.all_artifacts()) == 1
    assert commands_only.all_artifacts()[0].artifact_type == "command"


def test_filter_by_level(tmp_path: Path) -> None:
    """Test filtering artifacts by level."""
    user_dir = tmp_path / "user"
    project_dir = tmp_path / "project"

    # User skill
    user_skills = user_dir / ".claude" / "skills" / "user-skill"
    user_skills.mkdir(parents=True)
    (user_skills / "SKILL.md").write_text("# User Skill", encoding="utf-8")

    # Project skill
    project_skills = project_dir / ".claude" / "skills" / "project-skill"
    project_skills.mkdir(parents=True)
    (project_skills / "SKILL.md").write_text("# Project Skill", encoding="utf-8")

    discovery = UnifiedArtifactDiscovery()
    result = discovery.discover_all(project_dir=project_dir, user_home=user_dir)

    # Filter by USER level
    user_only = result.filter_by_level(ArtifactLevel.USER)
    assert len(user_only) == 1
    assert user_only[0].level == ArtifactLevel.USER

    # Filter by PROJECT level
    project_only = result.filter_by_level(ArtifactLevel.PROJECT)
    assert len(project_only) == 1
    assert project_only[0].level == ArtifactLevel.PROJECT


def test_filter_by_source(tmp_path: Path) -> None:
    """Test filtering artifacts by source."""
    project_dir = tmp_path / "project"
    project_claude = project_dir / ".claude"

    # Create local skill (not in config)
    local_skill = project_claude / "skills" / "local-skill"
    local_skill.mkdir(parents=True)
    (local_skill / "SKILL.md").write_text("# Local Skill", encoding="utf-8")

    # Create managed skill with config
    managed_skill = project_claude / "skills" / "managed-skill"
    managed_skill.mkdir(parents=True)
    (managed_skill / "SKILL.md").write_text("# Managed Skill", encoding="utf-8")

    # Create config marking one skill as managed
    config_content = """
version = "1"

[kits.test-kit]
kit_id = "test-kit"
version = "1.0.0"
source = "registry"
installed_at = "2024-01-01T00:00:00"
artifacts = ["skills/managed-skill/SKILL.md"]
"""
    config_path = project_claude / "dot-agent.toml"
    config_path.write_text(config_content, encoding="utf-8")

    discovery = UnifiedArtifactDiscovery()
    result = discovery.discover_all(project_dir=project_dir, user_home=tmp_path / "user")

    # Filter by LOCAL source
    local_only = result.filter_by_source(ArtifactSource.LOCAL)
    assert len(local_only.all_artifacts()) == 1
    assert local_only.all_artifacts()[0].source == ArtifactSource.LOCAL

    # Filter by MANAGED source
    managed_only = result.filter_by_source(ArtifactSource.MANAGED)
    assert len(managed_only.all_artifacts()) == 1
    assert managed_only.all_artifacts()[0].source == ArtifactSource.MANAGED


def test_discover_with_multiple_filters(tmp_path: Path) -> None:
    """Test discover_with_filters with multiple filter criteria."""
    project_dir = tmp_path / "project"
    project_claude = project_dir / ".claude"

    # Create project skill
    project_skill = project_claude / "skills" / "project-skill"
    project_skill.mkdir(parents=True)
    (project_skill / "SKILL.md").write_text("# Project Skill", encoding="utf-8")

    # Create project command
    commands_dir = project_claude / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "project-command.md").write_text("# Command", encoding="utf-8")

    # Create user skill
    user_dir = tmp_path / "user"
    user_skill = user_dir / ".claude" / "skills" / "user-skill"
    user_skill.mkdir(parents=True)
    (user_skill / "SKILL.md").write_text("# User Skill", encoding="utf-8")

    discovery = UnifiedArtifactDiscovery()

    # Filter: PROJECT level + skill type
    project_skills = discovery.discover_with_filters(
        artifact_type="skill",
        level=ArtifactLevel.PROJECT,
        project_dir=project_dir,
        user_home=user_dir,
    )

    assert len(project_skills) == 1
    assert project_skills[0].artifact_type == "skill"
    assert project_skills[0].level == ArtifactLevel.PROJECT

    # Filter: USER level only
    user_artifacts = discovery.discover_with_filters(
        level=ArtifactLevel.USER,
        project_dir=project_dir,
        user_home=user_dir,
    )

    assert len(user_artifacts) == 1
    assert user_artifacts[0].level == ArtifactLevel.USER


def test_handles_missing_directories(tmp_path: Path) -> None:
    """Test that discovery handles missing .claude directories gracefully."""
    # Use directories that don't have .claude subdirs
    user_dir = tmp_path / "user"
    project_dir = tmp_path / "project"
    user_dir.mkdir()
    project_dir.mkdir()

    discovery = UnifiedArtifactDiscovery()
    result = discovery.discover_all(project_dir=project_dir, user_home=user_dir)

    # Should return empty lists, not crash
    assert len(result.user_artifacts) == 0
    assert len(result.project_artifacts) == 0
    assert len(result.all_artifacts()) == 0


def test_discovers_hooks_from_both_levels(tmp_path: Path) -> None:
    """Test that hooks are discovered from both user and project levels."""
    user_dir = tmp_path / "user"
    project_dir = tmp_path / "project"

    # User hook
    user_claude = user_dir / ".claude"
    user_settings = {
        "hooks": {
            "user-prompt-submit": [
                {
                    "matcher": "**",
                    "hooks": [{"command": "python3 .claude/hooks/user/hook.py"}],
                }
            ]
        }
    }
    user_claude.mkdir(parents=True)
    (user_claude / "settings.json").write_text(json.dumps(user_settings), encoding="utf-8")
    user_hook = user_claude / "hooks" / "user" / "hook.py"
    user_hook.parent.mkdir(parents=True)
    user_hook.write_text("# User hook", encoding="utf-8")

    # Project hook
    project_claude = project_dir / ".claude"
    project_settings = {
        "hooks": {
            "pre-tool-use": [
                {
                    "matcher": "**.py",
                    "hooks": [{"command": "python3 .claude/hooks/project/hook.py"}],
                }
            ]
        }
    }
    project_claude.mkdir(parents=True)
    (project_claude / "settings.json").write_text(json.dumps(project_settings), encoding="utf-8")
    project_hook = project_claude / "hooks" / "project" / "hook.py"
    project_hook.parent.mkdir(parents=True)
    project_hook.write_text("# Project hook", encoding="utf-8")

    discovery = UnifiedArtifactDiscovery()
    result = discovery.discover_all(project_dir=project_dir, user_home=user_dir)

    # Should find hooks at both levels
    user_hooks = [a for a in result.user_artifacts if a.artifact_type == "hook"]
    project_hooks = [a for a in result.project_artifacts if a.artifact_type == "hook"]

    assert len(user_hooks) == 1
    assert len(project_hooks) == 1

    assert user_hooks[0].level == ArtifactLevel.USER
    assert project_hooks[0].level == ArtifactLevel.PROJECT
