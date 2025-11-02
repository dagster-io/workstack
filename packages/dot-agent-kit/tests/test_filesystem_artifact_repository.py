"""Integration tests for filesystem artifact repository."""

from pathlib import Path

from dot_agent_kit.io import create_default_config
from dot_agent_kit.models import ConflictPolicy, InstalledKit, ProjectConfig
from dot_agent_kit.models.artifact import ArtifactSource
from dot_agent_kit.repositories.filesystem_artifact_repository import (
    FilesystemArtifactRepository,
)


def test_discovers_skill_artifacts(tmp_path: Path) -> None:
    """Test that repository discovers skill artifacts correctly."""
    # Create test .claude/skills directory structure
    skills_dir = tmp_path / ".claude" / "skills"

    # Create a skill directory with SKILL.md
    test_skill = skills_dir / "test-skill"
    test_skill.mkdir(parents=True)
    (test_skill / "SKILL.md").write_text(
        "---\nname: test-skill\n---\n\n# Test Skill", encoding="utf-8"
    )

    # Create another skill
    another_skill = skills_dir / "another-skill"
    another_skill.mkdir(parents=True)
    (another_skill / "SKILL.md").write_text("# Another Skill", encoding="utf-8")

    # Create a directory without SKILL.md (should be ignored)
    invalid_skill = skills_dir / "not-a-skill"
    invalid_skill.mkdir(parents=True)
    (invalid_skill / "README.md").write_text("Not a skill", encoding="utf-8")

    repository = FilesystemArtifactRepository()
    config = create_default_config()
    artifacts = repository.discover_all_artifacts(tmp_path, config)

    # Should find exactly 2 skills
    skill_artifacts = [a for a in artifacts if a.artifact_type == "skill"]
    assert len(skill_artifacts) == 2

    # Check skill names
    skill_names = {a.artifact_name for a in skill_artifacts}
    assert skill_names == {"test-skill", "another-skill"}

    # All should be LOCAL since no kits in config
    assert all(a.source == ArtifactSource.LOCAL for a in skill_artifacts)


def test_discovers_command_artifacts(tmp_path: Path) -> None:
    """Test that repository discovers command artifacts correctly."""
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True)

    # Create a direct command file
    (commands_dir / "my-command.md").write_text("# My Command", encoding="utf-8")

    # Create a kit commands directory with commands
    kit_commands = commands_dir / "my-kit"
    kit_commands.mkdir()
    (kit_commands / "cmd1.md").write_text("# Command 1", encoding="utf-8")
    (kit_commands / "cmd2.md").write_text("# Command 2", encoding="utf-8")

    repository = FilesystemArtifactRepository()
    config = create_default_config()
    artifacts = repository.discover_all_artifacts(tmp_path, config)

    # Should find 3 commands
    command_artifacts = [a for a in artifacts if a.artifact_type == "command"]
    assert len(command_artifacts) == 3

    # Check command names
    command_names = {a.artifact_name for a in command_artifacts}
    assert command_names == {"my-command", "my-kit:cmd1", "my-kit:cmd2"}


def test_discovers_agent_artifacts(tmp_path: Path) -> None:
    """Test that repository discovers agent artifacts correctly."""
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)

    # Create a direct agent file
    (agents_dir / "my-agent.md").write_text("# My Agent", encoding="utf-8")

    # Create a kit agents directory with agents
    kit_agents = agents_dir / "devrun"
    kit_agents.mkdir()
    (kit_agents / "runner.md").write_text("# Runner Agent", encoding="utf-8")
    (kit_agents / "builder.md").write_text("# Builder Agent", encoding="utf-8")

    repository = FilesystemArtifactRepository()
    config = create_default_config()
    artifacts = repository.discover_all_artifacts(tmp_path, config)

    # Should find 3 agents
    agent_artifacts = [a for a in artifacts if a.artifact_type == "agent"]
    assert len(agent_artifacts) == 3

    # Check agent names
    agent_names = {a.artifact_name for a in agent_artifacts}
    assert agent_names == {"my-agent", "runner", "builder"}


def test_detects_managed_artifacts(tmp_path: Path) -> None:
    """Test that repository correctly identifies managed artifacts."""
    # Create skill structure
    skills_dir = tmp_path / ".claude" / "skills"
    skill_dir = skills_dir / "test-skill"
    skill_dir.mkdir(parents=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text("# Test Skill", encoding="utf-8")

    # Create config with this skill as managed
    config = ProjectConfig(
        version="1",
        default_conflict_policy=ConflictPolicy.ERROR,
        kits={
            "test-kit": InstalledKit(
                kit_id="test-kit",
                version="1.0.0",
                source="test",
                installed_at="2024-01-01T00:00:00",
                artifacts=["skills/test-skill/SKILL.md"],  # Without .claude prefix
            )
        },
    )

    repository = FilesystemArtifactRepository()
    artifacts = repository.discover_all_artifacts(tmp_path, config)

    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact.artifact_name == "test-skill"
    assert artifact.source == ArtifactSource.MANAGED
    assert artifact.kit_id == "test-kit"
    assert artifact.kit_version == "1.0.0"


def test_detects_unmanaged_artifacts_with_frontmatter(tmp_path: Path) -> None:
    """Test that repository correctly identifies unmanaged artifacts with frontmatter."""
    # Create skill with frontmatter
    skills_dir = tmp_path / ".claude" / "skills"
    skill_dir = skills_dir / "unmanaged-skill"
    skill_dir.mkdir(parents=True)
    skill_path = skill_dir / "SKILL.md"

    # Write skill with frontmatter indicating it came from a kit
    skill_content = """---
name: unmanaged-skill
description: An unmanaged skill
__dot_agent:
  kit_id: some-kit
  kit_version: 2.0.0
  artifact_type: skill
  artifact_path: skills/unmanaged-skill/SKILL.md
---

# Unmanaged Skill"""
    skill_path.write_text(skill_content, encoding="utf-8")

    # Config doesn't include this skill
    config = create_default_config()

    repository = FilesystemArtifactRepository()
    artifacts = repository.discover_all_artifacts(tmp_path, config)

    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact.artifact_name == "unmanaged-skill"
    assert artifact.source == ArtifactSource.UNMANAGED
    assert artifact.kit_id == "some-kit"
    assert artifact.kit_version == "2.0.0"


def test_handles_empty_claude_directory(tmp_path: Path) -> None:
    """Test that repository handles empty .claude directory gracefully."""
    # Create empty .claude directory
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    repository = FilesystemArtifactRepository()
    config = create_default_config()
    artifacts = repository.discover_all_artifacts(tmp_path, config)

    assert artifacts == []


def test_handles_missing_claude_directory(tmp_path: Path) -> None:
    """Test that repository handles missing .claude directory gracefully."""
    # Don't create .claude directory at all

    repository = FilesystemArtifactRepository()
    config = create_default_config()
    artifacts = repository.discover_all_artifacts(tmp_path, config)

    assert artifacts == []


def test_discovers_mixed_artifacts(tmp_path: Path) -> None:
    """Test that repository discovers all artifact types together correctly."""
    # Create various artifacts
    claude_dir = tmp_path / ".claude"

    # Skills
    skills_dir = claude_dir / "skills"
    skill_dir = skills_dir / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")

    # Commands
    commands_dir = claude_dir / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "my-command.md").write_text("# Command", encoding="utf-8")

    # Agents
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "my-agent.md").write_text("# Agent", encoding="utf-8")

    repository = FilesystemArtifactRepository()
    config = create_default_config()
    artifacts = repository.discover_all_artifacts(tmp_path, config)

    # Should find one of each type
    assert len(artifacts) == 3

    # Group by type
    by_type = {}
    for artifact in artifacts:
        by_type.setdefault(artifact.artifact_type, []).append(artifact)

    assert len(by_type["skill"]) == 1
    assert len(by_type["command"]) == 1
    assert len(by_type["agent"]) == 1

    assert by_type["skill"][0].artifact_name == "my-skill"
    assert by_type["command"][0].artifact_name == "my-command"
    assert by_type["agent"][0].artifact_name == "my-agent"


def test_handles_paths_with_claude_prefix_in_config(tmp_path: Path) -> None:
    """Test that repository handles config paths that include .claude/ prefix."""
    # Create skill
    skills_dir = tmp_path / ".claude" / "skills"
    skill_dir = skills_dir / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")

    # Config with .claude/ prefix in path
    config = ProjectConfig(
        version="1",
        default_conflict_policy=ConflictPolicy.ERROR,
        kits={
            "test-kit": InstalledKit(
                kit_id="test-kit",
                version="1.0.0",
                source="test",
                installed_at="2024-01-01T00:00:00",
                artifacts=[".claude/skills/test-skill/SKILL.md"],  # WITH .claude prefix
            )
        },
    )

    repository = FilesystemArtifactRepository()
    artifacts = repository.discover_all_artifacts(tmp_path, config)

    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact.source == ArtifactSource.MANAGED
    assert artifact.kit_id == "test-kit"


def test_ignores_non_md_files(tmp_path: Path) -> None:
    """Test that repository ignores non-markdown files."""
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True)

    # Create various file types
    (commands_dir / "command.md").write_text("# Command", encoding="utf-8")
    (commands_dir / "script.py").write_text("print('hello')", encoding="utf-8")
    (commands_dir / "notes.txt").write_text("Some notes", encoding="utf-8")
    (commands_dir / "README").write_text("Readme", encoding="utf-8")

    repository = FilesystemArtifactRepository()
    config = create_default_config()
    artifacts = repository.discover_all_artifacts(tmp_path, config)

    # Should only find the .md file
    assert len(artifacts) == 1
    assert artifacts[0].artifact_name == "command"
    assert artifacts[0].file_path == Path("commands/command.md")
