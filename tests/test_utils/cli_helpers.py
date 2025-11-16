"""Helpers for CLI testing with REAL git operations.

This module provides utilities for setting up isolated test environments
for CLI command tests that require REAL git operations (not fakes).

IMPORTANT: For 95% of CLI tests, use `simulated_workstack_env()` from
`tests.test_utils.env_helpers` instead. That helper uses FakeGitOps and
is faster, better isolated, and easier to use.

Only use `cli_test_repo()` when you specifically need:
- Real git operations (hooks, worktree edge cases)
- Actual filesystem permissions testing
- Real subprocess interactions
- Integration tests requiring actual git behavior

See: tests.test_utils.env_helpers.simulated_workstack_env() for the recommended pattern.
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
        erk_root: Path to workstacks directory
        tmp_path: Path to test root directory (contains .workstack config)
    """

    repo: Path
    erk_root: Path
    tmp_path: Path


@contextmanager
def cli_test_repo(tmp_path: Path) -> Generator[CLITestRepo]:
    """Set up isolated git repo with REAL git for CLI testing.

    ⚠️ WARNING: Only use this helper when you NEED real git operations!
    For 95% of CLI tests, use `simulated_workstack_env()` instead (from
    tests.test_utils.env_helpers), which is faster and better isolated.

    Creates a complete test environment with:
    - Isolated .workstack config directory with basic settings
    - REAL git repository with main branch and initial commit (subprocess calls)
    - erk_root directory structure
    - Configured git user (test@example.com / Test User)

    This helper handles boilerplate setup for CLI tests requiring REAL git.
    It does NOT create the CliRunner itself - tests must create that with
    isolated HOME environment and handle directory changes manually.

    When to use this helper:
    - Testing git hooks or git worktree edge cases
    - Testing actual filesystem permissions
    - Integration tests requiring actual git behavior

    When NOT to use this helper:
    - Regular CLI command tests → Use simulated_workstack_env() instead
    - Unit tests of core logic → Use FakeGitOps directly
    - Tests that can use fakes → Use simulated_workstack_env() instead

    Args:
        tmp_path: Pytest's tmp_path fixture providing isolated test directory

    Yields:
        CLITestRepo with repo path, erk_root, and tmp_path

    Example (real git required):
        ```python
        from click.testing import CliRunner
        from workstack.cli.cli import cli
        from tests.test_utils.cli_helpers import cli_test_repo

        def test_git_hook_integration(tmp_path: Path) -> None:
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

    Better alternative for most tests:
        ```python
        from click.testing import CliRunner
        from tests.test_utils.env_helpers import simulated_workstack_env

        def test_create_command() -> None:
            runner = CliRunner()
            with simulated_workstack_env(runner) as env:
                # Much simpler! No HOME setup, no os.chdir, uses fakes
                git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
                test_ctx = ErkContext.for_test(git_ops=git_ops, cwd=env.cwd)
                result = runner.invoke(cli, ["create", "feature"], obj=test_ctx)
        ```

    See Also:
        tests.test_utils.env_helpers.simulated_workstack_env() - Recommended helper
    """
    # Set up isolated global config
    global_config_dir = tmp_path / ".workstack"
    global_config_dir.mkdir()
    erk_root = tmp_path / "workstacks"
    (global_config_dir / "config.toml").write_text(
        f'workstacks_root = "{erk_root}"\nuse_graphite = false\n',
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

    yield CLITestRepo(repo=repo, erk_root=erk_root, tmp_path=tmp_path)
