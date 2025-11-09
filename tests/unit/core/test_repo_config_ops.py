"""Tests for repository config operations (validation and save)."""

from pathlib import Path

import pytest
from click.testing import CliRunner
from tests.fakes.gitops import FakeGitOps

from workstack.cli.config_schema import RepoConfig
from workstack.core.repo_config_ops import save_repo_config, validate_repo_config


def test_validate_repo_config_accepts_valid_config() -> None:
    """Test that valid config passes validation."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        repo_root = Path.cwd()
        git_dir = repo_root / ".git"
        git_dir.mkdir()

        # Create a branch for trunk_branch validation
        git_ops = FakeGitOps(
            git_common_dirs={repo_root: git_dir},
            all_branches=["main", "feature"],
        )

        config = RepoConfig(
            trunk_branch="main",
            env={"FOO": "bar"},
            post_create_commands=["echo hello"],
            post_create_shell=None,
        )

        # Should not raise
        validate_repo_config(repo_root, config, git_ops)


def test_validate_repo_config_rejects_nonexistent_trunk_branch() -> None:
    """Test that validation fails when trunk_branch doesn't exist."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        repo_root = Path.cwd()
        git_dir = repo_root / ".git"
        git_dir.mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={repo_root: git_dir},
            all_branches=["main", "feature"],
        )

        config = RepoConfig(
            trunk_branch="nonexistent",
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        # Should raise SystemExit
        with pytest.raises(SystemExit) as exc_info:
            validate_repo_config(repo_root, config, git_ops)

        assert exc_info.value.code == 1


def test_validate_repo_config_rejects_nonexistent_shell() -> None:
    """Test that validation fails when post_create_shell doesn't exist."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        repo_root = Path.cwd()
        git_dir = repo_root / ".git"
        git_dir.mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={repo_root: git_dir},
            all_branches=["main"],
        )

        config = RepoConfig(
            trunk_branch="main",
            env={},
            post_create_commands=[],
            post_create_shell="/nonexistent/shell",
        )

        # Should raise SystemExit
        with pytest.raises(SystemExit) as exc_info:
            validate_repo_config(repo_root, config, git_ops)

        assert exc_info.value.code == 1


def test_validate_repo_config_accepts_none_trunk_branch() -> None:
    """Test that None trunk_branch (auto-detect) is valid."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        repo_root = Path.cwd()
        git_dir = repo_root / ".git"
        git_dir.mkdir()

        git_ops = FakeGitOps(git_common_dirs={repo_root: git_dir})

        config = RepoConfig(
            trunk_branch=None,  # Auto-detect
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        # Should not raise
        validate_repo_config(repo_root, config, git_ops)


def test_save_repo_config_validates_before_save() -> None:
    """Test that save_repo_config validates config before writing."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        repo_root = Path.cwd()
        git_dir = repo_root / ".git"
        git_dir.mkdir()

        workstacks_dir = repo_root / ".workstack"
        workstacks_dir.mkdir()

        # Create pyproject.toml
        pyproject = repo_root / "pyproject.toml"
        pyproject.write_text("[tool.workstack]\n", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={repo_root: git_dir},
            all_branches=["main"],  # No "nonexistent" branch
        )

        # Invalid config
        config = RepoConfig(
            trunk_branch="nonexistent",  # This branch doesn't exist
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        # Should raise SystemExit during validation (before any files are written)
        with pytest.raises(SystemExit) as exc_info:
            save_repo_config(repo_root, workstacks_dir, config, git_ops)

        assert exc_info.value.code == 1


def test_save_repo_config_writes_valid_config() -> None:
    """Test that save_repo_config writes config to correct files."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        repo_root = Path.cwd()
        git_dir = repo_root / ".git"
        git_dir.mkdir()

        workstacks_dir = repo_root / ".workstack"
        workstacks_dir.mkdir()

        # Create pyproject.toml
        pyproject = repo_root / "pyproject.toml"
        pyproject.write_text("[tool.other]\nvalue = 1\n", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={repo_root: git_dir},
            all_branches=["main", "develop"],
        )

        config = RepoConfig(
            trunk_branch="develop",
            env={"MY_VAR": "my_value"},
            post_create_commands=["echo test"],
            post_create_shell="/bin/bash",
        )

        # Should write successfully
        save_repo_config(repo_root, workstacks_dir, config, git_ops)

        # Verify pyproject.toml was updated
        pyproject_content = pyproject.read_text(encoding="utf-8")
        assert "[tool.workstack]" in pyproject_content
        assert 'trunk_branch = "develop"' in pyproject_content

        # Verify config.toml was created
        config_file = workstacks_dir / "config.toml"
        assert config_file.exists()
        config_content = config_file.read_text(encoding="utf-8")
        assert "MY_VAR" in config_content
        assert "my_value" in config_content
        assert "echo test" in config_content
        assert "/bin/bash" in config_content
