"""Tests for init command."""

import os
from pathlib import Path

from click.testing import CliRunner

from dot_agent_kit.commands.init import init
from dot_agent_kit.io import load_project_config


def test_init_creates_config(tmp_project: Path, cli_runner: CliRunner) -> None:
    """Test that init creates dot-agent.toml with correct structure."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_project)
        result = cli_runner.invoke(init, [], catch_exceptions=False, obj={})

        assert result.exit_code == 0
        assert "Created" in result.output

        config_path = tmp_project / "dot-agent.toml"
        assert config_path.exists()

        config = load_project_config(tmp_project)
        assert config is not None
        assert config.version == "1"
        assert len(config.kits) == 0
    finally:
        os.chdir(original_cwd)


def test_init_creates_claude_directory(tmp_project: Path, cli_runner: CliRunner) -> None:
    """Test that init creates .claude/ directory if missing."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_project)
        result = cli_runner.invoke(init, [], catch_exceptions=False, obj={})

        assert result.exit_code == 0

        claude_dir = tmp_project / ".claude"
        assert claude_dir.exists()
        assert claude_dir.is_dir()
    finally:
        os.chdir(original_cwd)


def test_init_respects_force_flag(tmp_project: Path, cli_runner: CliRunner) -> None:
    """Test that init respects --force flag to overwrite existing config."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_project)
        # Create initial config
        result1 = cli_runner.invoke(init, [], catch_exceptions=False, obj={})
        assert result1.exit_code == 0

        # Try to init again without force - should fail
        result2 = cli_runner.invoke(init, [], catch_exceptions=False, obj={})
        assert result2.exit_code == 1
        assert "already exists" in result2.output

        # Try with force - should succeed
        result3 = cli_runner.invoke(init, ["--force"], catch_exceptions=False, obj={})
        assert result3.exit_code == 0
        assert "Created" in result3.output
    finally:
        os.chdir(original_cwd)


def test_init_errors_when_config_exists(tmp_project: Path, cli_runner: CliRunner) -> None:
    """Test that init errors appropriately when config exists (without --force)."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_project)
        # Create initial config
        result1 = cli_runner.invoke(init, [], catch_exceptions=False, obj={})
        assert result1.exit_code == 0

        # Try to init again - should fail with helpful message
        result2 = cli_runner.invoke(init, [], catch_exceptions=False, obj={})
        assert result2.exit_code == 1
        assert "Error: dot-agent.toml already exists" in result2.output
        assert "Use --force to overwrite" in result2.output
    finally:
        os.chdir(original_cwd)


def test_init_preserves_existing_claude_directory(tmp_project: Path, cli_runner: CliRunner) -> None:
    """Test that init doesn't fail if .claude/ directory already exists."""
    # Create .claude directory with content
    claude_dir = tmp_project / ".claude"
    claude_dir.mkdir()
    test_file = claude_dir / "test.txt"
    test_file.write_text("test content", encoding="utf-8")

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_project)
        # Run init
        result = cli_runner.invoke(init, [], catch_exceptions=False, obj={})
        assert result.exit_code == 0

        # Verify directory and file still exist
        assert claude_dir.exists()
        assert test_file.exists()
        assert test_file.read_text(encoding="utf-8") == "test content"
    finally:
        os.chdir(original_cwd)


def test_init_creates_agents_md(tmp_project: Path, cli_runner: CliRunner) -> None:
    """Test that init creates AGENTS.md with registry reference when missing."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_project)
        result = cli_runner.invoke(init, [], catch_exceptions=False, obj={})

        assert result.exit_code == 0

        # Verify AGENTS.md was created
        agents_md = tmp_project / "AGENTS.md"
        assert agents_md.exists()

        # Verify it contains required content
        content = agents_md.read_text(encoding="utf-8")
        assert "@.claude/docs/kit-registry.md" in content
        assert "## Installed Kit Documentation" in content
    finally:
        os.chdir(original_cwd)


def test_init_creates_registry_file(tmp_project: Path, cli_runner: CliRunner) -> None:
    """Test that init creates .claude/docs/kit-registry.md with proper structure."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_project)
        result = cli_runner.invoke(init, [], catch_exceptions=False, obj={})

        assert result.exit_code == 0

        # Verify registry file exists
        registry_file = tmp_project / ".claude" / "docs" / "kit-registry.md"
        assert registry_file.exists()

        # Verify it has proper structure
        content = registry_file.read_text(encoding="utf-8")
        assert "BEGIN_ENTRIES" in content
        assert "END_ENTRIES" in content
        assert "REGISTRY_VERSION: 1" in content
    finally:
        os.chdir(original_cwd)


def test_init_preserves_existing_agents_md(tmp_project: Path, cli_runner: CliRunner) -> None:
    """Test that init preserves existing AGENTS.md content and appends registry reference."""
    # Create AGENTS.md with custom content
    agents_md = tmp_project / "AGENTS.md"
    custom_content = "# My Custom Project\n\nThis is my existing content.\n"
    agents_md.write_text(custom_content, encoding="utf-8")

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_project)
        result = cli_runner.invoke(init, [], catch_exceptions=False, obj={})

        assert result.exit_code == 0

        # Verify original content is still present
        content = agents_md.read_text(encoding="utf-8")
        assert "# My Custom Project" in content
        assert "This is my existing content." in content

        # Verify registry reference was appended
        assert "@.claude/docs/kit-registry.md" in content
        assert "## Installed Kit Documentation" in content
    finally:
        os.chdir(original_cwd)


def test_init_skips_if_reference_exists(tmp_project: Path, cli_runner: CliRunner) -> None:
    """Test that init is idempotent and doesn't add duplicate references."""
    # Create AGENTS.md with registry reference already present
    agents_md = tmp_project / "AGENTS.md"
    content_with_reference = """# Project Docs

## Installed Kit Documentation

@.claude/docs/kit-registry.md
"""
    agents_md.write_text(content_with_reference, encoding="utf-8")

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_project)
        result = cli_runner.invoke(init, [], catch_exceptions=False, obj={})

        assert result.exit_code == 0

        # Verify file content is unchanged
        final_content = agents_md.read_text(encoding="utf-8")
        assert final_content == content_with_reference

        # Verify no duplicate references
        assert final_content.count("@.claude/docs/kit-registry.md") == 1
    finally:
        os.chdir(original_cwd)


def test_init_creates_registry_with_proper_structure(
    tmp_project: Path, cli_runner: CliRunner
) -> None:
    """Test that init creates registry file with all required markers and metadata."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_project)
        result = cli_runner.invoke(init, [], catch_exceptions=False, obj={})

        assert result.exit_code == 0

        # Read registry file
        registry_file = tmp_project / ".claude" / "docs" / "kit-registry.md"
        content = registry_file.read_text(encoding="utf-8")

        # Verify all required markers present
        assert "# Kit Documentation Registry" in content
        assert "AUTO-GENERATED" in content
        assert "DO NOT EDIT" in content
        assert "REGISTRY_VERSION: 1" in content
        assert "GENERATED_AT:" in content
        assert "<!-- BEGIN_ENTRIES -->" in content
        assert "<!-- END_ENTRIES -->" in content
    finally:
        os.chdir(original_cwd)
