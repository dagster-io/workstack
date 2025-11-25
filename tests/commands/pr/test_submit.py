"""Tests for erk pr submit command."""

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk.core.git.fake import FakeGit
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_submit_success() -> None:
    """Test successful PR submission with Claude executor."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )
        executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_pr_url="https://github.com/owner/repo/pull/123",
        )
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code == 0
        assert "https://github.com/owner/repo/pull/123" in result.output

        # Verify executor was called correctly
        assert len(executor.executed_commands) == 1
        command, worktree_path, dangerous, verbose = executor.executed_commands[0]
        assert command == "/gt:pr-submit"
        assert dangerous is False
        assert verbose is False


def test_pr_submit_with_dangerous_flag() -> None:
    """Test PR submission with --dangerous flag."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        result = runner.invoke(pr_group, ["submit", "--dangerous"], obj=ctx)

        assert result.exit_code == 0

        # Verify dangerous flag was passed to executor
        assert len(executor.executed_commands) == 1
        _, _, dangerous, _ = executor.executed_commands[0]
        assert dangerous is True


def test_pr_submit_with_verbose_flag() -> None:
    """Test PR submission with --verbose flag."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )
        executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        result = runner.invoke(pr_group, ["submit", "--verbose"], obj=ctx)

        assert result.exit_code == 0

        # Verify verbose flag was passed to executor
        assert len(executor.executed_commands) == 1
        _, _, _, verbose = executor.executed_commands[0]
        assert verbose is True


def test_pr_submit_fails_when_claude_not_available() -> None:
    """Test that command fails gracefully when Claude CLI is not available."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        executor = FakeClaudeExecutor(claude_available=False)
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "Claude CLI not found" in result.output


def test_pr_submit_fails_on_command_failure() -> None:
    """Test that command fails when Claude execution fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )
        executor = FakeClaudeExecutor(claude_available=True, command_should_fail=True)
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0


def test_pr_submit_with_both_flags() -> None:
    """Test PR submission with both --dangerous and --verbose flags."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )
        executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_pr_url="https://github.com/owner/repo/pull/456",
        )
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        result = runner.invoke(pr_group, ["submit", "--dangerous", "--verbose"], obj=ctx)

        assert result.exit_code == 0

        # Verify both flags were passed
        assert len(executor.executed_commands) == 1
        _, _, dangerous, verbose = executor.executed_commands[0]
        assert dangerous is True
        assert verbose is True


def test_pr_submit_displays_pr_url() -> None:
    """Test that PR URL is displayed prominently after successful submission."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-branch"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )
        executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_pr_url="https://github.com/owner/repo/pull/789",
        )
        ctx = build_workspace_test_context(env, git=git, claude_executor=executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code == 0
        # Verify PR URL is displayed with the 🔗 prefix
        assert "🔗 PR:" in result.output
        assert "https://github.com/owner/repo/pull/789" in result.output
