"""Tests for native implementation execution (Layer 3: Business Logic Tests).

These tests verify native execution logic using FakeShell.
No actual subprocess operations are performed.
"""

from pathlib import Path

import pytest
from tests.fakes.shell import FakeShell

from erk.core.native_implement import execute_native_implementation


def test_execute_native_implementation_checks_plan_exists(tmp_path: Path) -> None:
    """execute_native_implementation should check plan.md exists."""
    shell_ops = FakeShell()
    worktree = tmp_path / "my-worktree"
    worktree.mkdir()

    # No .plan/plan.md created

    with pytest.raises(FileNotFoundError, match="No plan found.*plan.md"):
        execute_native_implementation(shell_ops, worktree)


def test_execute_native_implementation_checks_claude_available(tmp_path: Path) -> None:
    """execute_native_implementation should check claude command available."""
    shell_ops = FakeShell(installed_tools={})  # No tools installed
    worktree = tmp_path / "my-worktree"
    worktree.mkdir()
    (worktree / ".plan").mkdir()
    (worktree / ".plan" / "plan.md").write_text("# Plan")

    with pytest.raises(FileNotFoundError, match="Claude Code CLI not found"):
        execute_native_implementation(shell_ops, worktree)


def test_execute_native_implementation_runs_claude_cli(tmp_path: Path) -> None:
    """execute_native_implementation should run claude with correct args."""
    shell_ops = FakeShell(
        installed_tools={"claude": "/usr/bin/claude"},
        command_exit_code=0,
    )
    worktree = tmp_path / "my-worktree"
    worktree.mkdir()
    (worktree / ".plan").mkdir()
    (worktree / ".plan" / "plan.md").write_text("# Plan")

    exit_code = execute_native_implementation(shell_ops, worktree)

    # Should call run_command with correct command
    assert len(shell_ops.command_calls) == 1
    command, cwd = shell_ops.command_calls[0]
    assert command == [
        "claude",
        "--permission-mode",
        "acceptEdits",
        "/erk:implement-plan",
    ]
    assert cwd == worktree

    # Should return exit code
    assert exit_code == 0


def test_execute_native_implementation_propagates_exit_code(tmp_path: Path) -> None:
    """execute_native_implementation should propagate claude exit code."""
    shell_ops = FakeShell(
        installed_tools={"claude": "/usr/bin/claude"},
        command_exit_code=42,
    )
    worktree = tmp_path / "my-worktree"
    worktree.mkdir()
    (worktree / ".plan").mkdir()
    (worktree / ".plan" / "plan.md").write_text("# Plan")

    exit_code = execute_native_implementation(shell_ops, worktree)

    assert exit_code == 42
