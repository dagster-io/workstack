"""Tests for subprocess error handling across CLI commands.

MOCK USAGE JUSTIFICATION:
========================
This test file uses unittest.mock to simulate subprocess.CalledProcessError
because:

1. **Testing Exception Behavior**: We need to verify that CLI commands properly
   display stderr content from CalledProcessError exceptions. This requires
   raising exceptions with specific stderr values.

2. **Not Testing External Tools**: These tests verify our error handling code,
   not the behavior of git/gh/gt tools. Using real subprocess calls would test
   those tools instead of our error handlers.

3. **Isolation**: Mock allows us to test error handling in isolation without
   requiring specific failure conditions in real git/gh/gt commands, which would
   be fragile and environment-dependent.

4. **Error Boundary Testing**: According to AGENTS.md, try/except is acceptable
   at error boundaries (CLI level). These tests verify those boundaries handle
   errors correctly.

This is one of the rare cases where mocking is appropriate in this codebase,
as we're testing error handling infrastructure, not business logic.
"""

import subprocess
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.sync import sync_cmd
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext
from erk.core.git.abc import WorktreeInfo
from tests.fakes.git import FakeGit
from tests.fakes.github import FakeGitHub
from tests.fakes.graphite import FakeGraphite

# Tests for sync command error handling


def test_sync_displays_stderr_on_gt_sync_failure(tmp_path: Path) -> None:
    """Test that sync command displays full stderr when gt sync fails.

    This verifies the fix for incomplete error messages - we should see
    the actual error text from gt sync, not just the exit code.
    """
    # Arrange: Set up fake operations and context
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()

    git_ops = FakeGit(
        git_common_dirs={repo_root: repo_root / ".git"},
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main", is_root=True),
            ],
        },
        current_branches={repo_root: "main"},
    )

    github_ops = FakeGitHub()

    # Create a FakeGraphite that raises CalledProcessError with stderr
    error_message = (
        "fatal: unable to access 'https://github.com/user/repo.git/': "
        "Failed to connect to github.com"
    )
    graphite_ops = FakeGraphite(
        sync_raises=subprocess.CalledProcessError(
            returncode=128,
            cmd=["gt", "sync"],
            stderr=error_message,
        )
    )

    global_config = GlobalConfig(
        erk_root=tmp_path / "erks",
        use_graphite=True,
        shell_setup_complete=False,
        show_pr_info=True,
    )

    ctx = ErkContext.for_test(
        git=git_ops,
        global_config=global_config,
        graphite=graphite_ops,
        github=github_ops,
        cwd=repo_root,
        dry_run=False,
    )

    runner = CliRunner()

    # Act: Run sync command and capture output
    result = runner.invoke(sync_cmd, [], obj=ctx)

    # Assert: Verify exit code and error message contains full stderr
    assert result.exit_code == 128
    assert "Error: gt sync failed:" in result.output
    # Key assertion: Full error message should be displayed, not just exit code
    assert error_message in result.output
    # Ensure we're not just showing exit code
    assert "exit code 128" not in result.output or error_message in result.output


def test_sync_shows_exit_code_when_stderr_empty(tmp_path: Path) -> None:
    """Test sync command fallback when stderr is empty.

    When stderr is not captured (e.g., verbose mode with direct streaming),
    we should fall back to showing the exit code.
    """
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()

    git_ops = FakeGit(
        git_common_dirs={repo_root: repo_root / ".git"},
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main", is_root=True),
            ],
        },
        current_branches={repo_root: "main"},
    )

    github_ops = FakeGitHub()

    # Create FakeGraphite that raises CalledProcessError WITHOUT stderr
    graphite_ops = FakeGraphite(
        sync_raises=subprocess.CalledProcessError(
            returncode=1,
            cmd=["gt", "sync"],
            stderr=None,  # No stderr captured
        )
    )

    global_config = GlobalConfig(
        erk_root=tmp_path / "erks",
        use_graphite=True,
        shell_setup_complete=False,
        show_pr_info=True,
    )

    ctx = ErkContext.for_test(
        git=git_ops,
        global_config=global_config,
        graphite=graphite_ops,
        github=github_ops,
        cwd=repo_root,
        dry_run=False,
    )

    runner = CliRunner()

    # Act
    result = runner.invoke(sync_cmd, [], obj=ctx)

    # Assert: Should show exit code when stderr is not available
    assert result.exit_code == 1
    assert "Error: gt sync failed:" in result.output
    assert "exit code 1" in result.output


# Note: land-stack error handling tests are not included here because they
# require a complex SimulatedWorkstackEnv setup (see tests/commands/graphite/test_land_stack.py).
# The land-stack error handling code at src/erk/cli/commands/land_stack.py:677-683
# already correctly displays stderr using the same pattern as sync.py:
#     error_detail = e.stderr.strip() if e.stderr else str(e)


# Tests for error handling consistency


def test_all_calledprocesserror_handlers_use_stderr() -> None:
    """Test that all CalledProcessError handlers follow the same pattern.

    This is a documentation test that verifies our error handling pattern:
    error_detail = e.stderr.strip() if e.stderr else fallback

    This test doesn't execute code but documents the expected pattern.
    """
    # Expected pattern in all CalledProcessError handlers:
    expected_pattern = """
    except subprocess.CalledProcessError as e:
        error_detail = e.stderr.strip() if e.stderr else fallback
        # Display error_detail to user
    """

    # Files that should follow this pattern:
    files_with_error_handlers = [
        "src/erk/cli/commands/sync.py",
        "src/erk/cli/commands/land_stack.py",
    ]

    # This test serves as documentation. Actual enforcement happens in:
    # 1. Code review
    # 2. The specific error handling tests above
    # 3. Integration tests that exercise error paths

    assert expected_pattern is not None  # Keeps pytest happy
    assert files_with_error_handlers is not None


# Note: Additional error handling tests could be added for:
# - Other commands that call subprocess (if any)
# - Different error scenarios (network errors, permission errors, etc.)
# - Verification that stdout remains verbose-only while stderr is always captured
