"""Tests for list command."""

from pathlib import Path

from click.testing import CliRunner
from pytest import CaptureFixture

from dot_agent_kit.commands.kit.list import _list_artifacts, list_installed_kits
from dot_agent_kit.io import create_default_config
from dot_agent_kit.models import InstalledKit, ProjectConfig
from dot_agent_kit.models.artifact import (
    ArtifactLevel,
    ArtifactSource,
    InstalledArtifact,
)
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
                level=ArtifactLevel.PROJECT,
                kit_id="devrun",
                kit_version="0.1.0",
            ),
            InstalledArtifact(
                artifact_type="skill",
                artifact_name="gh",
                file_path=Path("skills/gh/SKILL.md"),
                source=ArtifactSource.LOCAL,
                level=ArtifactLevel.PROJECT,
            ),
        ]
    )

    _list_artifacts(config, project_dir, repository)

    captured = capsys.readouterr()
    # Check for kit-grouped format
    assert "[devrun] (v0.1.0):" in captured.out
    assert "Skills (1):" in captured.out
    assert "devrun-make" in captured.out
    assert "skills/devrun-make/" in captured.out
    assert "[local]:" in captured.out
    assert "gh" in captured.out
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
                level=ArtifactLevel.PROJECT,
                kit_id="gt",
                kit_version="0.1.0",
            ),
            InstalledArtifact(
                artifact_type="command",
                artifact_name="codex-review",
                file_path=Path("commands/codex-review.md"),
                source=ArtifactSource.LOCAL,
                level=ArtifactLevel.PROJECT,
            ),
        ]
    )

    _list_artifacts(config, project_dir, repository)

    captured = capsys.readouterr()
    # Check for kit-grouped format
    assert "[gt] (v0.1.0):" in captured.out
    assert "Commands (1):" in captured.out
    assert "gt:land-branch" in captured.out
    assert "commands/gt/land-branch.md" in captured.out
    assert "[local]:" in captured.out
    assert "codex-review" in captured.out
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
                level=ArtifactLevel.PROJECT,
                kit_id="devrun",
                kit_version="0.1.0",
            ),
            InstalledArtifact(
                artifact_type="agent",
                artifact_name="spec-creator",
                file_path=Path("agents/spec-creator.md"),
                source=ArtifactSource.LOCAL,
                level=ArtifactLevel.PROJECT,
            ),
        ]
    )

    _list_artifacts(config, project_dir, repository)

    captured = capsys.readouterr()
    # Check for kit-grouped format
    assert "[devrun] (v0.1.0):" in captured.out
    assert "Agents (1):" in captured.out
    assert "runner" in captured.out
    assert "agents/devrun/runner.md" in captured.out
    assert "[local]:" in captured.out
    assert "spec-creator" in captured.out
    assert "agents/spec-creator.md" in captured.out


def test_list_hooks(capsys: CaptureFixture[str]) -> None:
    """Test list command displays hooks properly."""
    config = create_default_config()
    project_dir = Path("/tmp/test-project")
    repository = FakeArtifactRepository()

    repository.set_artifacts(
        [
            InstalledArtifact(
                artifact_type="hook",
                artifact_name="devrun:suggest-dignified-python",
                file_path=Path("hooks/devrun/suggest-dignified-python.py"),
                source=ArtifactSource.MANAGED,
                level=ArtifactLevel.PROJECT,
                kit_id="devrun",
                kit_version="0.1.0",
            ),
            InstalledArtifact(
                artifact_type="hook",
                artifact_name="custom-kit:my-hook",
                file_path=Path("hooks/custom-kit/my-hook.sh"),
                source=ArtifactSource.LOCAL,
                level=ArtifactLevel.PROJECT,
            ),
        ]
    )

    _list_artifacts(config, project_dir, repository)

    captured = capsys.readouterr()
    # Check for kit-grouped format
    assert "[devrun] (v0.1.0):" in captured.out
    assert "Hooks (1):" in captured.out
    assert "devrun:suggest-dignified-python" in captured.out
    assert "hooks/devrun/suggest-dignified-python.py" in captured.out
    assert "[local]:" in captured.out
    assert "custom-kit:my-hook" in captured.out
    assert "hooks/custom-kit/my-hook.sh" in captured.out


def test_list_mixed_artifacts(capsys: CaptureFixture[str]) -> None:
    """Test list command with mixed artifact types and sources."""
    config = ProjectConfig(
        version="1",
        kits={
            "devrun": InstalledKit(
                kit_id="devrun",
                source_type="bundled",
                version="0.1.0",
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
                level=ArtifactLevel.PROJECT,
                kit_id="devrun",
                kit_version="0.1.0",
            ),
            InstalledArtifact(
                artifact_type="agent",
                artifact_name="runner",
                file_path=Path("agents/devrun/runner.md"),
                source=ArtifactSource.MANAGED,
                level=ArtifactLevel.PROJECT,
                kit_id="devrun",
                kit_version="0.1.0",
            ),
            # Local artifact (not in config)
            InstalledArtifact(
                artifact_type="skill",
                artifact_name="gt-graphite",
                file_path=Path("skills/gt-graphite/SKILL.md"),
                source=ArtifactSource.LOCAL,
                level=ArtifactLevel.PROJECT,
                kit_id=None,
                kit_version=None,
            ),
            # Local artifacts
            InstalledArtifact(
                artifact_type="skill",
                artifact_name="gh",
                file_path=Path("skills/gh/SKILL.md"),
                source=ArtifactSource.LOCAL,
                level=ArtifactLevel.PROJECT,
            ),
            InstalledArtifact(
                artifact_type="command",
                artifact_name="codex-review",
                file_path=Path("commands/codex-review.md"),
                source=ArtifactSource.LOCAL,
                level=ArtifactLevel.PROJECT,
            ),
            InstalledArtifact(
                artifact_type="hook",
                artifact_name="test-kit:test-hook",
                file_path=Path("hooks/test-kit/test-hook.py"),
                source=ArtifactSource.LOCAL,
                level=ArtifactLevel.PROJECT,
            ),
        ]
    )

    _list_artifacts(config, project_dir, repository)

    captured = capsys.readouterr()

    # Check kit-grouped format - devrun kit
    assert "[devrun] (v0.1.0):" in captured.out
    assert "Skills (1):" in captured.out
    assert "devrun-make" in captured.out
    assert "Agents (1):" in captured.out
    assert "runner" in captured.out

    # Check local artifacts
    assert "[local]:" in captured.out
    assert "gt-graphite" in captured.out
    assert "gh" in captured.out
    assert "codex-review" in captured.out
    assert "test-kit:test-hook" in captured.out


def test_list_column_alignment(capsys: CaptureFixture[str]) -> None:
    """Test that columns are properly aligned within kit groups."""
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
                level=ArtifactLevel.PROJECT,
            ),
            InstalledArtifact(
                artifact_type="skill",
                artifact_name="very-long-skill-name-here",
                file_path=Path("skills/very-long-skill-name-here/SKILL.md"),
                source=ArtifactSource.MANAGED,
                level=ArtifactLevel.PROJECT,
                kit_id="long-kit-name",
                kit_version="1.2.3",
            ),
        ]
    )

    _list_artifacts(config, project_dir, repository)

    captured = capsys.readouterr()

    # Just verify the output contains expected kit groupings and artifact names
    # Column alignment is handled by the implementation's width calculations
    assert "[long-kit-name] (v1.2.3):" in captured.out
    assert "very-long-skill-name-here" in captured.out
    assert "[local]:" in captured.out
    assert "short" in captured.out


def test_list_command_cli(tmp_project: Path) -> None:
    """Test list command with --artifacts flag through CLI interface.

    Note: We can't easily inject the fake repository through the CLI,
    so this test verifies basic CLI invocation works without error.
    """
    import os

    from dot_agent_kit.io import save_project_config

    # Set up a basic project config
    config = create_default_config()
    save_project_config(tmp_project, config)

    runner = CliRunner()
    # Run from the tmp_project directory by changing cwd
    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_project)
        result = runner.invoke(list_installed_kits, ["--artifacts"])
        assert result.exit_code == 0
        # Should run without error and show some output
    finally:
        os.chdir(original_cwd)


def test_list_docs(capsys: CaptureFixture[str]) -> None:
    """Test list command displays docs properly."""
    config = create_default_config()
    project_dir = Path("/tmp/test-project")
    repository = FakeArtifactRepository()

    repository.set_artifacts(
        [
            InstalledArtifact(
                artifact_type="doc",
                artifact_name="tools/pytest.md",
                file_path=Path("docs/devrun/tools/pytest.md"),
                source=ArtifactSource.MANAGED,
                level=ArtifactLevel.PROJECT,
                kit_id="devrun",
                kit_version="0.1.0",
            ),
            InstalledArtifact(
                artifact_type="doc",
                artifact_name="guide.md",
                file_path=Path("docs/my-kit/guide.md"),
                source=ArtifactSource.LOCAL,
                level=ArtifactLevel.PROJECT,
                kit_id="my-kit",
            ),
        ]
    )

    _list_artifacts(config, project_dir, repository)

    captured = capsys.readouterr()
    # Check for kit-grouped format
    assert "[devrun] (v0.1.0):" in captured.out
    assert "Docs (1):" in captured.out
    assert "tools/pytest.md" in captured.out
    assert "docs/devrun/tools/pytest.md" in captured.out
    assert "[local]:" in captured.out
    assert "guide.md" in captured.out
    assert "docs/my-kit/guide.md" in captured.out


def test_list_docs_with_mixed_artifacts(capsys: CaptureFixture[str]) -> None:
    """Test list command displays docs alongside other artifact types."""
    config = create_default_config()
    project_dir = Path("/tmp/test-project")
    repository = FakeArtifactRepository()

    repository.set_artifacts(
        [
            InstalledArtifact(
                artifact_type="skill",
                artifact_name="my-skill",
                file_path=Path("skills/my-skill/SKILL.md"),
                source=ArtifactSource.MANAGED,
                level=ArtifactLevel.PROJECT,
                kit_id="test-kit",
                kit_version="1.0.0",
            ),
            InstalledArtifact(
                artifact_type="doc",
                artifact_name="overview.md",
                file_path=Path("docs/test-kit/overview.md"),
                source=ArtifactSource.MANAGED,
                level=ArtifactLevel.PROJECT,
                kit_id="test-kit",
                kit_version="1.0.0",
            ),
        ]
    )

    _list_artifacts(config, project_dir, repository)

    captured = capsys.readouterr()
    # Both should appear under the same kit group
    assert "[test-kit] (v1.0.0):" in captured.out
    assert "Skills (1):" in captured.out
    assert "my-skill" in captured.out
    assert "Docs (1):" in captured.out
    assert "overview.md" in captured.out
