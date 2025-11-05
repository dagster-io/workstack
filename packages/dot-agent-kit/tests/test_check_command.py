"""Tests for check command."""

from pathlib import Path

from click.testing import CliRunner

from dot_agent_kit.commands.check import (
    check,
    check_artifact_sync,
    validate_kit_fields,
)
from dot_agent_kit.io import save_project_config
from dot_agent_kit.models import InstalledKit, ProjectConfig


def test_check_artifact_sync_both_files_identical(tmp_path: Path) -> None:
    """Test sync check when both files exist and are identical."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    bundled_base = tmp_path / "bundled"
    bundled_base.mkdir()

    # Create identical files
    local_path = project_dir / ".claude" / "skills" / "test" / "SKILL.md"
    local_path.parent.mkdir(parents=True)
    local_path.write_text("test content", encoding="utf-8")

    bundled_path = bundled_base / "skills" / "test" / "SKILL.md"
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text("test content", encoding="utf-8")

    result = check_artifact_sync(
        project_dir,
        ".claude/skills/test/SKILL.md",
        bundled_base,
    )

    assert result.is_in_sync is True
    assert result.reason is None


def test_check_artifact_sync_local_missing(tmp_path: Path) -> None:
    """Test sync check when local file is missing."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    bundled_base = tmp_path / "bundled"
    bundled_base.mkdir()

    # Create only bundled file
    bundled_path = bundled_base / "skills" / "test" / "SKILL.md"
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text("test content", encoding="utf-8")

    result = check_artifact_sync(
        project_dir,
        ".claude/skills/test/SKILL.md",
        bundled_base,
    )

    assert result.is_in_sync is False
    assert result.reason == "Local artifact missing"


def test_check_artifact_sync_bundled_missing(tmp_path: Path) -> None:
    """Test sync check when bundled file is missing."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    bundled_base = tmp_path / "bundled"
    bundled_base.mkdir()

    # Create only local file
    local_path = project_dir / ".claude" / "skills" / "test" / "SKILL.md"
    local_path.parent.mkdir(parents=True)
    local_path.write_text("test content", encoding="utf-8")

    result = check_artifact_sync(
        project_dir,
        ".claude/skills/test/SKILL.md",
        bundled_base,
    )

    assert result.is_in_sync is False
    assert result.reason == "Bundled artifact missing"


def test_check_artifact_sync_content_differs(tmp_path: Path) -> None:
    """Test sync check when files exist but content differs."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    bundled_base = tmp_path / "bundled"
    bundled_base.mkdir()

    # Create files with different content
    local_path = project_dir / ".claude" / "skills" / "test" / "SKILL.md"
    local_path.parent.mkdir(parents=True)
    local_path.write_text("local content", encoding="utf-8")

    bundled_path = bundled_base / "skills" / "test" / "SKILL.md"
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text("bundled content", encoding="utf-8")

    result = check_artifact_sync(
        project_dir,
        ".claude/skills/test/SKILL.md",
        bundled_base,
    )

    assert result.is_in_sync is False
    assert result.reason == "Content differs"


def test_check_artifact_sync_path_handling_with_claude_prefix(tmp_path: Path) -> None:
    """Test that .claude/ prefix is properly stripped when checking bundled path."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    bundled_base = tmp_path / "bundled"
    bundled_base.mkdir()

    # Create identical files
    local_path = project_dir / ".claude" / "skills" / "test" / "SKILL.md"
    local_path.parent.mkdir(parents=True)
    local_path.write_text("test content", encoding="utf-8")

    # Bundled path should NOT have .claude/ prefix
    bundled_path = bundled_base / "skills" / "test" / "SKILL.md"
    bundled_path.parent.mkdir(parents=True)
    bundled_path.write_text("test content", encoding="utf-8")

    # Pass artifact path with .claude/ prefix
    result = check_artifact_sync(
        project_dir,
        ".claude/skills/test/SKILL.md",
        bundled_base,
    )

    assert result.is_in_sync is True


def test_check_command_no_artifacts(tmp_path: Path) -> None:
    """Test check command when no artifacts exist."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()
        config = ProjectConfig(version="1", kits={})
        save_project_config(project_dir, config)

        result = runner.invoke(check)

        assert result.exit_code == 0
        assert "No artifacts found to validate" in result.output
        assert "No kits installed" in result.output
        assert "All checks passed" in result.output


def test_check_command_valid_artifacts(tmp_path: Path) -> None:
    """Test check command with valid artifacts."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create valid artifact
        skill_path = project_dir / ".claude" / "skills" / "test" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test",
            encoding="utf-8",
        )

        # Create config
        config = ProjectConfig(
            version="1",
            kits={
                "test-kit": InstalledKit(
                    kit_id="test-kit",
                    version="1.0.0",
                    source_type="package",
                    installed_at="2024-01-01T00:00:00",
                    artifacts=["skills/test/SKILL.md"],
                ),
            },
        )
        save_project_config(project_dir, config)

        result = runner.invoke(check)

        assert result.exit_code == 0
        assert "Validated 1 artifacts" in result.output
        assert "All artifacts are valid" in result.output


def test_check_command_invalid_artifacts(tmp_path: Path) -> None:
    """Test check command with invalid artifacts."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create .claude directory but no artifacts
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Create config with artifact that doesn't exist
        config = ProjectConfig(
            version="1",
            kits={
                "test-kit": InstalledKit(
                    kit_id="test-kit",
                    version="1.0.0",
                    source_type="package",
                    installed_at="2024-01-01T00:00:00",
                    artifacts=["skills/missing/SKILL.md"],
                ),
            },
        )
        save_project_config(project_dir, config)

        result = runner.invoke(check)

        assert result.exit_code == 1
        assert "✗ Invalid:" in result.output
        assert "Some checks failed" in result.output


def test_check_command_no_bundled_kits(tmp_path: Path) -> None:
    """Test check command when no bundled kits are installed."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create valid artifact from non-bundled source
        skill_path = project_dir / ".claude" / "skills" / "test" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test",
            encoding="utf-8",
        )

        # Create config with non-bundled kit
        config = ProjectConfig(
            version="1",
            kits={
                "test-kit": InstalledKit(
                    kit_id="test-kit",
                    version="1.0.0",
                    source_type="package",
                    installed_at="2024-01-01T00:00:00",
                    artifacts=["skills/test/SKILL.md"],
                ),
            },
        )
        save_project_config(project_dir, config)

        result = runner.invoke(check)

        assert result.exit_code == 0
        assert "No bundled kits found to check" in result.output
        assert "All checks passed" in result.output


def test_check_command_verbose_flag(tmp_path: Path) -> None:
    """Test check command with verbose flag shows detailed output."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create valid artifact
        skill_path = project_dir / ".claude" / "skills" / "test" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test",
            encoding="utf-8",
        )

        # Create config
        config = ProjectConfig(
            version="1",
            kits={
                "test-kit": InstalledKit(
                    kit_id="test-kit",
                    version="1.0.0",
                    source_type="package",
                    installed_at="2024-01-01T00:00:00",
                    artifacts=["skills/test/SKILL.md"],
                ),
            },
        )
        save_project_config(project_dir, config)

        result = runner.invoke(check, ["--verbose"])

        assert result.exit_code == 0
        assert "✓" in result.output  # Should show checkmarks for valid artifacts


def test_check_command_no_config(tmp_path: Path) -> None:
    """Test check command when no config file exists."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(check)

        assert result.exit_code == 0
        assert "No artifacts found to validate" in result.output
        assert "No dot-agent.toml found - skipping sync check" in result.output
        assert "All checks passed" in result.output


def test_validate_kit_fields_all_valid() -> None:
    """Test validate_kit_fields with all valid fields."""
    kit = InstalledKit(
        kit_id="test-kit",
        source_type="bundled",
        version="1.0.0",
        installed_at="2024-01-01T00:00:00",
        artifacts=[".claude/skills/test/SKILL.md"],
    )
    errors = validate_kit_fields(kit)
    assert len(errors) == 0


def test_validate_kit_fields_empty_kit_id() -> None:
    """Test validate_kit_fields with empty kit_id."""
    kit = InstalledKit(
        kit_id="",
        source_type="bundled",
        version="1.0.0",
        installed_at="2024-01-01T00:00:00",
        artifacts=[".claude/skills/test/SKILL.md"],
    )
    errors = validate_kit_fields(kit)
    assert len(errors) == 1
    assert "kit_id is empty" in errors


def test_validate_kit_fields_empty_version() -> None:
    """Test validate_kit_fields with empty version."""
    kit = InstalledKit(
        kit_id="test-kit",
        source_type="bundled",
        version="",
        installed_at="2024-01-01T00:00:00",
        artifacts=[".claude/skills/test/SKILL.md"],
    )
    errors = validate_kit_fields(kit)
    assert len(errors) == 1
    assert "version is empty" in errors


def test_validate_kit_fields_invalid_source_type() -> None:
    """Test validate_kit_fields with invalid source_type."""
    kit = InstalledKit(
        kit_id="test-kit",
        source_type="invalid",
        version="1.0.0",
        installed_at="2024-01-01T00:00:00",
        artifacts=[".claude/skills/test/SKILL.md"],
    )
    errors = validate_kit_fields(kit)
    assert len(errors) == 1
    assert "Invalid source_type" in errors[0]


def test_validate_kit_fields_empty_artifacts() -> None:
    """Test validate_kit_fields with empty artifacts list."""
    kit = InstalledKit(
        kit_id="test-kit",
        source_type="bundled",
        version="1.0.0",
        installed_at="2024-01-01T00:00:00",
        artifacts=[],
    )
    errors = validate_kit_fields(kit)
    assert len(errors) == 1
    assert "artifacts list is empty" in errors


def test_validate_kit_fields_empty_installed_at() -> None:
    """Test validate_kit_fields with empty installed_at."""
    kit = InstalledKit(
        kit_id="test-kit",
        source_type="bundled",
        version="1.0.0",
        installed_at="",
        artifacts=[".claude/skills/test/SKILL.md"],
    )
    errors = validate_kit_fields(kit)
    assert len(errors) == 1
    assert "installed_at is empty" in errors


def test_validate_kit_fields_multiple_errors() -> None:
    """Test validate_kit_fields with multiple validation errors."""
    kit = InstalledKit(
        kit_id="",
        source_type="invalid",
        version="",
        installed_at="",
        artifacts=[],
    )
    errors = validate_kit_fields(kit)
    assert len(errors) == 5
    assert any("kit_id is empty" in e for e in errors)
    assert any("version is empty" in e for e in errors)
    assert any("Invalid source_type" in e for e in errors)
    assert any("artifacts list is empty" in e for e in errors)
    assert any("installed_at is empty" in e for e in errors)


def test_check_command_bundled_kit_sync_in_sync(tmp_path: Path) -> None:
    """Test check command with bundled kit when artifacts are in sync."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = Path.cwd()

        # Create .claude directory
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Create config with bundled kit
        # Note: We use "bundled:devrun" which is a real bundled kit in the package
        config = ProjectConfig(
            version="1",
            kits={
                "devrun": InstalledKit(
                    kit_id="devrun",
                    version="0.1.0",
                    source_type="bundled",
                    installed_at="2024-01-01T00:00:00",
                    artifacts=["agents/devrun/devrun.md"],
                ),
            },
        )
        save_project_config(project_dir, config)

        # Create local artifact that matches bundled version
        # Read bundled artifact content
        from dot_agent_kit.sources import BundledKitSource

        bundled_source = BundledKitSource()
        bundled_path = bundled_source._get_bundled_kit_path("devrun")
        if bundled_path is not None:
            bundled_artifact = bundled_path / "agents" / "devrun" / "devrun.md"
            if bundled_artifact.exists():
                bundled_content = bundled_artifact.read_text(encoding="utf-8")

                # Create local artifact with same content
                local_artifact = claude_dir / "agents" / "devrun" / "devrun.md"
                local_artifact.parent.mkdir(parents=True)
                local_artifact.write_text(bundled_content, encoding="utf-8")

                result = runner.invoke(check)

                assert result.exit_code == 0
                assert "All artifacts are in sync" in result.output
                assert "Warning: Could not find bundled kit" not in result.output
