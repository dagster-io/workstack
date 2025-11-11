"""Helpers for CLI testing with CliRunner.

This module provides utilities for setting up isolated test environments
for CLI command tests using Click's CliRunner pattern.
"""

import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CLITestRepo:
    """Test environment for CLI tests with isolated git repo and config.

    Attributes:
        repo: Path to git repository (with initial commit)
        workstacks_root: Path to workstacks directory
        tmp_path: Path to test root directory (contains .workstack config)
    """

    repo: Path
    workstacks_root: Path
    tmp_path: Path


@contextmanager
def cli_test_repo(tmp_path: Path) -> Generator[CLITestRepo]:
    """Set up isolated git repo with workstack config for CLI testing.

    Creates a complete test environment with:
    - Isolated .workstack config directory with basic settings
    - Real git repository with main branch and initial commit
    - workstacks_root directory structure
    - Configured git user (test@example.com / Test User)

    This helper handles all the boilerplate setup needed for CLI tests that
    invoke workstack commands via CliRunner. It does NOT create the CliRunner
    itself - tests should create that with isolated HOME environment.

    Args:
        tmp_path: Pytest's tmp_path fixture providing isolated test directory

    Yields:
        CLITestRepo with repo path, workstacks_root, and tmp_path

    Example:
        ```python
        from click.testing import CliRunner
        from workstack.cli.cli import cli
        from tests.test_utils.cli_helpers import cli_test_repo

        def test_create_command(tmp_path: Path) -> None:
            with cli_test_repo(tmp_path) as test_env:
                # Set up CliRunner with isolated HOME
                env_vars = os.environ.copy()
                env_vars["HOME"] = str(test_env.tmp_path)
                runner = CliRunner(env=env_vars)

                # Run test from repo directory
                original_cwd = os.getcwd()
                try:
                    os.chdir(test_env.repo)
                    result = runner.invoke(cli, ["create", "feature"])
                    assert result.exit_code == 0
                finally:
                    os.chdir(original_cwd)
        ```

    Note:
        This helper is designed for tests that need a standard git repository
        setup. For tests that need custom git state (multiple worktrees,
        specific branch configurations, etc.), set up git manually instead.
    """
    # Set up isolated global config
    global_config_dir = tmp_path / ".workstack"
    global_config_dir.mkdir()
    workstacks_root = tmp_path / "workstacks"
    (global_config_dir / "config.toml").write_text(
        f'workstacks_root = "{workstacks_root}"\nuse_graphite = false\n',
        encoding="utf-8",
    )

    # Set up real git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)

    # Create initial commit
    (repo / "README.md").write_text("test", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True)

    yield CLITestRepo(repo=repo, workstacks_root=workstacks_root, tmp_path=tmp_path)
