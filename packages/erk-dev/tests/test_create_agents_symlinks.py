"""Tests for create-agents-symlinks command."""

from pathlib import Path

from click.testing import CliRunner

from erk_dev.cli import cli
from erk_dev.commands.create_agents_symlinks import command


def test_is_git_repo_root_with_git_dir() -> None:
    """Test is_git_repo_root returns True when .git exists."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create a .git directory
        git_dir = Path.cwd() / ".git"
        git_dir.mkdir()

        assert command.is_git_repo_root(Path.cwd())


def test_is_git_repo_root_without_git_dir() -> None:
    """Test is_git_repo_root returns False when .git doesn't exist."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        assert not command.is_git_repo_root(Path.cwd())


def test_is_git_repo_root_with_git_file() -> None:
    """Test is_git_repo_root returns False when .git is a file."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create .git as a file (not a directory)
        git_file = Path.cwd() / ".git"
        git_file.write_text("gitdir: ../somewhere", encoding="utf-8")

        assert not command.is_git_repo_root(Path.cwd())


def test_create_reference_for_agents_md_creates_new_file() -> None:
    """Test creating a new CLAUDE.md reference when it doesn't exist."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create an AGENTS.md file
        agents_md = Path.cwd() / "AGENTS.md"
        agents_md.write_text("# Project instructions", encoding="utf-8")

        # Create reference file
        status = command.create_reference_for_agents_md(agents_md, dry_run=False)

        assert status == "created"
        claude_md = Path.cwd() / "CLAUDE.md"
        assert claude_md.exists()
        assert claude_md.is_file()
        assert claude_md.read_text(encoding="utf-8") == "@AGENTS.md"


def test_create_reference_for_agents_md_dry_run() -> None:
    """Test dry run mode doesn't create reference file."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create an AGENTS.md file
        agents_md = Path.cwd() / "AGENTS.md"
        agents_md.write_text("# Project instructions", encoding="utf-8")

        # Try to create reference in dry-run mode
        status = command.create_reference_for_agents_md(agents_md, dry_run=True)

        assert status == "created"
        claude_md = Path.cwd() / "CLAUDE.md"
        assert not claude_md.exists()


def test_create_reference_for_agents_md_skips_correct_reference() -> None:
    """Test skipping when CLAUDE.md already contains @AGENTS.md."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create an AGENTS.md file
        agents_md = Path.cwd() / "AGENTS.md"
        agents_md.write_text("# Project instructions", encoding="utf-8")

        # Create correct reference file
        claude_md = Path.cwd() / "CLAUDE.md"
        claude_md.write_text("@AGENTS.md", encoding="utf-8")

        # Should skip
        status = command.create_reference_for_agents_md(agents_md, dry_run=False)

        assert status == "skipped_correct"
        assert claude_md.is_file()
        assert claude_md.read_text(encoding="utf-8") == "@AGENTS.md"


def test_create_reference_for_agents_md_skips_different_file() -> None:
    """Test skipping when CLAUDE.md exists with different content."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create an AGENTS.md file
        agents_md = Path.cwd() / "AGENTS.md"
        agents_md.write_text("# Project instructions", encoding="utf-8")

        # Create CLAUDE.md with different content
        claude_md = Path.cwd() / "CLAUDE.md"
        claude_md.write_text("# Different content", encoding="utf-8")

        # Should skip
        status = command.create_reference_for_agents_md(agents_md, dry_run=False)

        assert status == "skipped_exists"
        assert claude_md.exists()
        assert claude_md.read_text(encoding="utf-8") == "# Different content"


def test_create_reference_for_agents_md_skips_symlink() -> None:
    """Test skipping when CLAUDE.md is a symlink."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create files
        agents_md = Path.cwd() / "AGENTS.md"
        agents_md.write_text("# Project instructions", encoding="utf-8")
        other_file = Path.cwd() / "OTHER.md"
        other_file.write_text("# Other content", encoding="utf-8")

        # Create CLAUDE.md as symlink to OTHER.md
        claude_md = Path.cwd() / "CLAUDE.md"
        claude_md.symlink_to("OTHER.md")

        # Should skip
        status = command.create_reference_for_agents_md(agents_md, dry_run=False)

        assert status == "skipped_exists"
        assert claude_md.is_symlink()
        assert claude_md.readlink() == Path("OTHER.md")


def test_create_agents_symlinks_finds_multiple_files() -> None:
    """Test finding and creating references for multiple AGENTS.md files."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        repo_root = Path.cwd()

        # Create multiple AGENTS.md files
        (repo_root / "AGENTS.md").write_text("# Root", encoding="utf-8")
        (repo_root / "sub1").mkdir()
        (repo_root / "sub1" / "AGENTS.md").write_text("# Sub1", encoding="utf-8")
        (repo_root / "sub2").mkdir()
        (repo_root / "sub2" / "AGENTS.md").write_text("# Sub2", encoding="utf-8")

        created, skipped = command.create_agents_symlinks(repo_root, dry_run=False, verbose=False)

        assert created == 3
        assert skipped == 0
        assert (repo_root / "CLAUDE.md").is_file()
        assert (repo_root / "CLAUDE.md").read_text(encoding="utf-8") == "@AGENTS.md"
        assert (repo_root / "sub1" / "CLAUDE.md").is_file()
        assert (repo_root / "sub2" / "CLAUDE.md").is_file()


def test_create_agents_symlinks_idempotent() -> None:
    """Test running twice is idempotent."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        repo_root = Path.cwd()

        # Create AGENTS.md file
        (repo_root / "AGENTS.md").write_text("# Root", encoding="utf-8")

        # First run
        created1, skipped1 = command.create_agents_symlinks(repo_root, dry_run=False, verbose=False)
        assert created1 == 1
        assert skipped1 == 0

        # Second run
        created2, skipped2 = command.create_agents_symlinks(repo_root, dry_run=False, verbose=False)
        assert created2 == 0
        assert skipped2 == 1


def test_create_agents_symlinks_no_agents_files() -> None:
    """Test behavior when no AGENTS.md files exist."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        repo_root = Path.cwd()

        created, skipped = command.create_agents_symlinks(repo_root, dry_run=False, verbose=False)

        assert created == 0
        assert skipped == 0


def test_cli_help() -> None:
    """Test create-agents-symlinks help output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["create-agents-symlinks", "--help"])
    assert result.exit_code == 0
    assert "Create CLAUDE.md reference" in result.output
    assert "--dry-run" in result.output
    assert "--verbose" in result.output


def test_cli_not_in_git_repo() -> None:
    """Test error when not in git repository root."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # No .git directory
        result = runner.invoke(cli, ["create-agents-symlinks"])
        # Script execution fails, CLI should exit with non-zero code
        assert result.exit_code == 1
