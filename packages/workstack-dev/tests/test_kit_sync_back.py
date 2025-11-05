"""Tests for kit-sync-back command."""

from pathlib import Path

from click.testing import CliRunner

from workstack_dev.cli import cli
from workstack_dev.commands.kit_sync_back import command


def create_test_kit_structure(
    project_dir: Path,
    kit_id: str,
    artifact_paths: list[str],
) -> None:
    """Create test kit structure with installed files and source directory.

    Args:
        project_dir: Project directory path
        kit_id: Kit identifier
        artifact_paths: List of artifact paths to create
    """
    # Create installed files in .claude/
    for artifact_path in artifact_paths:
        full_path = project_dir / artifact_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(f"Installed content for {artifact_path}", encoding="utf-8")

    # Create kit source directory
    kit_source_dir = (
        project_dir
        / "packages"
        / "dot-agent-kit"
        / "src"
        / "dot_agent_kit"
        / "data"
        / "kits"
        / kit_id
    )
    kit_source_dir.mkdir(parents=True, exist_ok=True)

    # Create kit.yaml
    kit_yaml = kit_source_dir / "kit.yaml"
    kit_yaml.write_text(
        f'name: "{kit_id}"\nversion: "0.1.0"\ndescription: "Test kit"\n',
        encoding="utf-8",
    )

    # Create source files (with different content to detect sync)
    for artifact_path in artifact_paths:
        parts = Path(artifact_path).parts
        if len(parts) >= 3:
            artifact_type = parts[1]  # e.g., "skills"
            rest_parts = parts[2:]  # Everything after .claude/{type}/
            source_path = kit_source_dir / artifact_type / Path(*rest_parts)
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_text(f"Original source for {artifact_path}", encoding="utf-8")


def create_dot_agent_toml(project_dir: Path, kit_id: str, artifacts: list[str]) -> None:
    """Create a minimal dot-agent.toml file.

    Args:
        project_dir: Project directory path
        kit_id: Kit identifier
        artifacts: List of artifact paths
    """
    config_path = project_dir / "dot-agent.toml"
    artifacts_str = "\n    ".join(f'"{a}",' for a in artifacts)
    config_content = f"""version = "1"

[kits.{kit_id}]
kit_id = "{kit_id}"
source_type = "bundled"
version = "0.1.0"
installed_at = "2025-11-02T00:00:00"
artifacts = [
    {artifacts_str}
]
"""
    config_path.write_text(config_content, encoding="utf-8")


def test_get_kit_source_dir_finds_kit() -> None:
    """Test get_kit_source_dir finds kit in project structure."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        project_dir = Path.cwd()
        kit_id = "test-kit"

        # Create kit directory
        kit_dir = (
            project_dir
            / "packages"
            / "dot-agent-kit"
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / kit_id
        )
        kit_dir.mkdir(parents=True, exist_ok=True)

        # Should find it
        result = command.get_kit_source_dir(kit_id)
        assert result == kit_dir


def test_map_artifact_to_source_skill() -> None:
    """Test mapping skill artifact to source path."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        project_dir = Path.cwd()
        kit_id = "test-kit"

        # Create kit directory
        kit_dir = (
            project_dir
            / "packages"
            / "dot-agent-kit"
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / kit_id
        )
        kit_dir.mkdir(parents=True, exist_ok=True)

        artifact_path = ".claude/skills/test-skill/SKILL.md"
        expected_source = kit_dir / "skills" / "test-skill" / "SKILL.md"

        result = command.map_artifact_to_source(artifact_path, kit_id)
        assert result == expected_source


def test_map_artifact_to_source_command() -> None:
    """Test mapping command artifact to source path."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        project_dir = Path.cwd()
        kit_id = "test-kit"

        # Create kit directory
        kit_dir = (
            project_dir
            / "packages"
            / "dot-agent-kit"
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / kit_id
        )
        kit_dir.mkdir(parents=True, exist_ok=True)

        artifact_path = ".claude/commands/test/my-command.md"
        expected_source = kit_dir / "commands" / "test" / "my-command.md"

        result = command.map_artifact_to_source(artifact_path, kit_id)
        assert result == expected_source


def test_sync_file_to_source_syncs_file() -> None:
    """Test syncing a single file from installed to source."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        installed_path = Path.cwd() / "installed.txt"
        source_path = Path.cwd() / "source" / "file.txt"

        installed_path.write_text("New content", encoding="utf-8")

        result = command.sync_file_to_source(
            installed_path, source_path, dry_run=False, verbose=False
        )

        assert result is True
        assert source_path.exists()
        assert source_path.read_text(encoding="utf-8") == "New content"


def test_sync_file_to_source_dry_run() -> None:
    """Test dry run doesn't actually sync."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        installed_path = Path.cwd() / "installed.txt"
        source_path = Path.cwd() / "source" / "file.txt"

        installed_path.write_text("New content", encoding="utf-8")

        result = command.sync_file_to_source(
            installed_path, source_path, dry_run=True, verbose=False
        )

        assert result is True
        assert not source_path.exists()


def test_sync_file_to_source_skips_missing() -> None:
    """Test skipping when installed file doesn't exist."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        installed_path = Path.cwd() / "missing.txt"
        source_path = Path.cwd() / "source" / "file.txt"

        result = command.sync_file_to_source(
            installed_path, source_path, dry_run=False, verbose=False
        )

        assert result is False
        assert not source_path.exists()


def test_sync_directory_to_source_syncs_recursively() -> None:
    """Test syncing directory recursively."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        installed_dir = Path.cwd() / "installed"
        source_dir = Path.cwd() / "source"

        # Create nested structure
        (installed_dir / "subdir").mkdir(parents=True, exist_ok=True)
        (installed_dir / "file1.txt").write_text("File 1", encoding="utf-8")
        (installed_dir / "subdir" / "file2.txt").write_text("File 2", encoding="utf-8")

        count = command.sync_directory_to_source(
            installed_dir, source_dir, dry_run=False, verbose=False
        )

        assert count == 2
        assert (source_dir / "file1.txt").exists()
        assert (source_dir / "subdir" / "file2.txt").exists()
        assert (source_dir / "file1.txt").read_text(encoding="utf-8") == "File 1"
        assert (source_dir / "subdir" / "file2.txt").read_text(encoding="utf-8") == "File 2"


def test_sync_kit_artifacts_basic() -> None:
    """Test syncing basic kit artifacts."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        project_dir = Path.cwd()
        kit_id = "test-kit"
        artifacts = [".claude/skills/test-skill/SKILL.md"]

        create_test_kit_structure(project_dir, kit_id, artifacts)

        count = command.sync_kit_artifacts(
            kit_id, artifacts, project_dir, dry_run=False, verbose=False
        )

        assert count == 1
        kit_source_dir = (
            project_dir
            / "packages"
            / "dot-agent-kit"
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / kit_id
        )
        source_file = kit_source_dir / "skills" / "test-skill" / "SKILL.md"
        assert source_file.exists()
        assert "Installed content" in source_file.read_text(encoding="utf-8")


def test_sync_kit_artifacts_with_subdirectories() -> None:
    """Test syncing kit artifacts with subdirectories like references/."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        project_dir = Path.cwd()
        kit_id = "test-kit"
        artifacts = [".claude/skills/test-skill/SKILL.md"]

        create_test_kit_structure(project_dir, kit_id, artifacts)

        # Create references subdirectory
        references_dir = project_dir / ".claude" / "skills" / "test-skill" / "references"
        references_dir.mkdir(parents=True, exist_ok=True)
        (references_dir / "ref1.md").write_text("Reference 1", encoding="utf-8")
        (references_dir / "ref2.md").write_text("Reference 2", encoding="utf-8")

        count = command.sync_kit_artifacts(
            kit_id, artifacts, project_dir, dry_run=False, verbose=False
        )

        # Should sync main file + 2 reference files
        assert count == 3
        kit_source_dir = (
            project_dir
            / "packages"
            / "dot-agent-kit"
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / kit_id
        )
        assert (kit_source_dir / "skills" / "test-skill" / "references" / "ref1.md").exists()
        assert (kit_source_dir / "skills" / "test-skill" / "references" / "ref2.md").exists()


def test_cli_no_config() -> None:
    """Test error when no dot-agent.toml exists."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["kit-sync-back"])
        assert result.exit_code == 1
        assert "No dot-agent.toml found" in result.output


def test_cli_no_kits() -> None:
    """Test behavior when no kits are installed."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create empty config
        (Path.cwd() / "dot-agent.toml").write_text('version = "1"\n', encoding="utf-8")

        result = runner.invoke(cli, ["kit-sync-back"])
        assert result.exit_code == 0
        assert "No kits installed" in result.output


def test_cli_sync_single_kit() -> None:
    """Test syncing a single kit with --kit option."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        project_dir = Path.cwd()
        kit_id = "test-kit"
        artifacts = [".claude/skills/test-skill/SKILL.md"]

        create_test_kit_structure(project_dir, kit_id, artifacts)
        create_dot_agent_toml(project_dir, kit_id, artifacts)

        result = runner.invoke(cli, ["kit-sync-back", "--kit", kit_id])
        assert result.exit_code == 0
        assert "Synced 1 file(s) total" in result.output


def test_cli_sync_nonexistent_kit() -> None:
    """Test error when specified kit doesn't exist."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        project_dir = Path.cwd()
        kit_id = "test-kit"
        artifacts = [".claude/skills/test-skill/SKILL.md"]

        create_test_kit_structure(project_dir, kit_id, artifacts)
        create_dot_agent_toml(project_dir, kit_id, artifacts)

        result = runner.invoke(cli, ["kit-sync-back", "--kit", "nonexistent"])
        assert result.exit_code == 1
        assert "not installed" in result.output


def test_cli_dry_run() -> None:
    """Test --dry-run option doesn't actually sync."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        project_dir = Path.cwd()
        kit_id = "test-kit"
        artifacts = [".claude/skills/test-skill/SKILL.md"]

        create_test_kit_structure(project_dir, kit_id, artifacts)
        create_dot_agent_toml(project_dir, kit_id, artifacts)

        # Get original source content
        kit_source_dir = (
            project_dir
            / "packages"
            / "dot-agent-kit"
            / "src"
            / "dot_agent_kit"
            / "data"
            / "kits"
            / kit_id
        )
        source_file = kit_source_dir / "skills" / "test-skill" / "SKILL.md"
        original_content = source_file.read_text(encoding="utf-8")

        result = runner.invoke(cli, ["kit-sync-back", "--dry-run"])
        assert result.exit_code == 0
        assert "Would sync 1 file(s) total" in result.output

        # Source file should be unchanged
        assert source_file.read_text(encoding="utf-8") == original_content


def test_cli_help() -> None:
    """Test kit-sync-back help output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["kit-sync-back", "--help"])
    assert result.exit_code == 0
    assert "Sync kit files from .claude/ back to their source" in result.output
    assert "--kit" in result.output
    assert "--dry-run" in result.output
    assert "--verbose" in result.output
