"""Tests for list command."""

from pathlib import Path

from click.testing import CliRunner
from pytest import CaptureFixture

from dot_agent_kit.commands.artifact.list import _list_artifacts, list_cmd, ls_cmd
from dot_agent_kit.io import create_default_config
from dot_agent_kit.models import ConflictPolicy, InstalledKit, ProjectConfig
from dot_agent_kit.models.artifact import ArtifactSource, InstalledArtifact
from tests.fakes.fake_artifact_repository import FakeArtifactRepository


def test_list_no_artifacts(capsys: CaptureFixture[str]) -> None:
    """Test list command when no artifacts are installed."""
    config = create_default_config()
    project_dir = Path("/tmp/test-project")
    repository = FakeArtifactRepository()  # Empty by default

    _list_artifacts(config, project_dir, repository)

    captured = capsys.readouterr()
    assert "No artifacts installed" in captured.out


def test_list_skills(capsys: CaptureFixture[str]) -> None:
    """Test list command displays skills properly."""
    config = create_default_config()
    project_dir = Path("/tmp/test-project")
    repository = FakeArtifactRepository()

    # Set up test data directly - no mocking needed!
    repository.set_artifacts(
        [
            InstalledArtifact(
                artifact_type="skill",
                artifact_name="devrun-make",
                file_path=Path("skills/devrun-make/SKILL.md"),
                source=ArtifactSource.MANAGED,
                kit_id="devrun",
                kit_version="0.1.0",
            ),
            InstalledArtifact(
                artifact_type="skill",
                artifact_name="gh",
                file_path=Path("skills/gh/SKILL.md"),
                source=ArtifactSource.LOCAL,
            ),
        ]
    )

    _list_artifacts(config, project_dir, repository)

    captured = capsys.readouterr()
    assert "Skills:" in captured.out
    assert "devrun-make" in captured.out
    assert "[devrun@0.1.0]" in captured.out
    assert "skills/devrun-make/" in captured.out
    assert "gh" in captured.out
    assert "[local]" in captured.out
    assert "skills/gh/" in captured.out


def test_list_commands(capsys: CaptureFixture[str]) -> None:
    """Test list command displays commands properly."""
    config = create_default_config()
    project_dir = Path("/tmp/test-project")
    repository = FakeArtifactRepository()

    repository.set_artifacts(
        [
            InstalledArtifact(
                artifact_type="command",
                artifact_name="gt:land-branch",
                file_path=Path("commands/gt/land-branch.md"),
                source=ArtifactSource.MANAGED,
                kit_id="gt",
                kit_version="0.1.0",
            ),
            InstalledArtifact(
                artifact_type="command",
                artifact_name="codex-review",
                file_path=Path("commands/codex-review.md"),
                source=ArtifactSource.LOCAL,
            ),
        ]
    )

    _list_artifacts(config, project_dir, repository)

    captured = capsys.readouterr()
    assert "Commands:" in captured.out
    assert "gt:land-branch" in captured.out
    assert "[gt@0.1.0]" in captured.out
    assert "commands/gt/land-branch.md" in captured.out
    assert "codex-review" in captured.out
    assert "[local]" in captured.out
    assert "commands/codex-review.md" in captured.out


def test_list_agents(capsys: CaptureFixture[str]) -> None:
    """Test list command displays agents properly."""
    config = create_default_config()
    project_dir = Path("/tmp/test-project")
    repository = FakeArtifactRepository()

    repository.set_artifacts(
        [
            InstalledArtifact(
                artifact_type="agent",
                artifact_name="runner",
                file_path=Path("agents/devrun/runner.md"),
                source=ArtifactSource.MANAGED,
                kit_id="devrun",
                kit_version="0.1.0",
            ),
            InstalledArtifact(
                artifact_type="agent",
                artifact_name="spec-creator",
                file_path=Path("agents/spec-creator.md"),
                source=ArtifactSource.LOCAL,
            ),
        ]
    )

    _list_artifacts(config, project_dir, repository)

    captured = capsys.readouterr()
    assert "Agents:" in captured.out
    assert "runner" in captured.out
    assert "[devrun@0.1.0]" in captured.out
    assert "agents/devrun/runner.md" in captured.out
    assert "spec-creator" in captured.out
    assert "[local]" in captured.out
    assert "agents/spec-creator.md" in captured.out


def test_list_mixed_artifacts(capsys: CaptureFixture[str]) -> None:
    """Test list command with mixed artifact types and sources."""
    config = ProjectConfig(
        version="1",
        default_conflict_policy=ConflictPolicy.ERROR,
        kits={
            "devrun": InstalledKit(
                kit_id="devrun",
                version="0.1.0",
                source="bundled",
                installed_at="2024-01-01T00:00:00",
                artifacts=["skills/devrun-make/SKILL.md", "agents/devrun/runner.md"],
            )
        },
    )
    project_dir = Path("/tmp/test-project")
    repository = FakeArtifactRepository()

    repository.set_artifacts(
        [
            # Managed artifacts
            InstalledArtifact(
                artifact_type="skill",
                artifact_name="devrun-make",
                file_path=Path("skills/devrun-make/SKILL.md"),
                source=ArtifactSource.MANAGED,
                kit_id="devrun",
                kit_version="0.1.0",
            ),
            InstalledArtifact(
                artifact_type="agent",
                artifact_name="runner",
                file_path=Path("agents/devrun/runner.md"),
                source=ArtifactSource.MANAGED,
                kit_id="devrun",
                kit_version="0.1.0",
            ),
            # Local artifact (not in config)
            InstalledArtifact(
                artifact_type="skill",
                artifact_name="gt-graphite",
                file_path=Path("skills/gt-graphite/SKILL.md"),
                source=ArtifactSource.LOCAL,
                kit_id=None,
                kit_version=None,
            ),
            # Local artifacts
            InstalledArtifact(
                artifact_type="skill",
                artifact_name="gh",
                file_path=Path("skills/gh/SKILL.md"),
                source=ArtifactSource.LOCAL,
            ),
            InstalledArtifact(
                artifact_type="command",
                artifact_name="codex-review",
                file_path=Path("commands/codex-review.md"),
                source=ArtifactSource.LOCAL,
            ),
        ]
    )

    _list_artifacts(config, project_dir, repository)

    captured = capsys.readouterr()

    # Check skills section
    assert "Skills:" in captured.out
    assert "devrun-make" in captured.out
    assert "[devrun@0.1.0]" in captured.out
    assert "gt-graphite" in captured.out
    assert "gh" in captured.out
    assert "[local]" in captured.out

    # Check commands section
    assert "Commands:" in captured.out
    assert "codex-review" in captured.out

    # Check agents section
    assert "Agents:" in captured.out
    assert "runner" in captured.out


def test_list_column_alignment(capsys: CaptureFixture[str]) -> None:
    """Test that columns are properly aligned."""
    config = create_default_config()
    project_dir = Path("/tmp/test-project")
    repository = FakeArtifactRepository()

    repository.set_artifacts(
        [
            InstalledArtifact(
                artifact_type="skill",
                artifact_name="short",
                file_path=Path("skills/short/SKILL.md"),
                source=ArtifactSource.LOCAL,
            ),
            InstalledArtifact(
                artifact_type="skill",
                artifact_name="very-long-skill-name-here",
                file_path=Path("skills/very-long-skill-name-here/SKILL.md"),
                source=ArtifactSource.MANAGED,
                kit_id="long-kit-name",
                kit_version="1.2.3",
            ),
        ]
    )

    _list_artifacts(config, project_dir, repository)

    captured = capsys.readouterr()
    lines = captured.out.strip().split("\n")

    # Find skill lines (skip header)
    skill_lines = [line for line in lines if line.startswith("  ") and line.strip()]

    # Check that columns are aligned (source brackets should start at same position)
    # Note: Skills have layout: name | folder_path | file_counts | source
    # Commands/Agents have layout: name | source | file_path
    if len(skill_lines) >= 2:
        # Find position of '[' in each line
        bracket_positions = [line.index("[") for line in skill_lines if "[" in line]
        # All brackets should be at the same position
        assert len(set(bracket_positions)) == 1, "Source columns are not aligned"


def test_list_command_cli() -> None:
    """Test list command through CLI interface.

    Note: We can't easily inject the fake repository through the CLI,
    so this test verifies basic CLI invocation works without error.
    """
    runner = CliRunner()
    result = runner.invoke(list_cmd)
    assert result.exit_code == 0
    # Should run without error and show some output


def test_ls_command_cli() -> None:
    """Test ls command (alias) through CLI interface.

    Note: We can't easily inject the fake repository through the CLI,
    so this test verifies basic CLI invocation works without error.
    """
    runner = CliRunner()
    result = runner.invoke(ls_cmd)
    assert result.exit_code == 0
    # Should run without error and show some output
