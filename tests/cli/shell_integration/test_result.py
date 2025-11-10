"""Tests for shell integration result helpers."""

import sys
import tempfile
from io import StringIO
from pathlib import Path

import pytest

from workstack.cli.shell_integration.result import (
    activate_root_repo,
    activate_worktree,
    finish_with_activation,
    finish_with_cd,
)
from workstack.core.repo_discovery import RepoContext


def test_activate_root_repo_script_mode() -> None:
    """Test activate_root_repo in script mode outputs script path."""
    original_stdout = sys.stdout
    captured_stdout = StringIO()

    try:
        sys.stdout = captured_stdout
        repo = RepoContext(
            root=Path("/test/repo"),
            repo_name="test-repo",
            workstacks_dir=Path("/test/repo/workstacks"),
        )

        with pytest.raises(SystemExit) as exc_info:
            activate_root_repo(repo, script=True, command_name="switch")

        # Should exit with code 0
        assert exc_info.value.code == 0

        # Should output a temp file path (no newline at end)
        output = captured_stdout.getvalue()
        assert output.startswith(tempfile.gettempdir())
        assert output.endswith(".sh")
        assert not output.endswith("\n")

        # Verify the script file was created
        script_path = Path(output)
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")
        assert "cd " in script_content
        assert 'echo "Switched to root repo: $(pwd)"' in script_content

        # Clean up
        script_path.unlink()
    finally:
        sys.stdout = original_stdout


def test_activate_root_repo_non_script_mode() -> None:
    """Test activate_root_repo in non-script mode outputs instructions."""
    original_stdout = sys.stdout
    captured_stdout = StringIO()

    try:
        sys.stdout = captured_stdout
        repo = RepoContext(
            root=Path("/test/repo"),
            repo_name="test-repo",
            workstacks_dir=Path("/test/repo/workstacks"),
        )

        with pytest.raises(SystemExit) as exc_info:
            activate_root_repo(repo, script=False, command_name="switch")

        # Should exit with code 0
        assert exc_info.value.code == 0

        # Should output instructions
        output = captured_stdout.getvalue()
        assert "Switched to root repo: /test/repo" in output
        assert "Shell integration not detected" in output
        assert "source <(workstack switch root --script)" in output
    finally:
        sys.stdout = original_stdout


def test_activate_worktree_script_mode(tmp_path: Path) -> None:
    """Test activate_worktree in script mode outputs script path."""
    original_stdout = sys.stdout
    captured_stdout = StringIO()

    try:
        sys.stdout = captured_stdout
        repo = RepoContext(
            root=Path("/test/repo"),
            repo_name="test-repo",
            workstacks_dir=Path("/test/repo/workstacks"),
        )

        # Create a test worktree directory
        worktree_path = tmp_path / "test-worktree"
        worktree_path.mkdir()

        with pytest.raises(SystemExit) as exc_info:
            activate_worktree(repo, worktree_path, script=True, command_name="switch")

        # Should exit with code 0
        assert exc_info.value.code == 0

        # Should output a temp file path (no newline at end)
        output = captured_stdout.getvalue()
        assert output.startswith(tempfile.gettempdir())
        assert output.endswith(".sh")
        assert not output.endswith("\n")

        # Verify the script file was created
        script_path = Path(output)
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")
        assert "cd " in script_content
        assert str(worktree_path) in script_content

        # Clean up
        script_path.unlink()
    finally:
        sys.stdout = original_stdout


def test_activate_worktree_non_script_mode(tmp_path: Path) -> None:
    """Test activate_worktree in non-script mode outputs instructions."""
    original_stdout = sys.stdout
    captured_stdout = StringIO()

    try:
        sys.stdout = captured_stdout
        repo = RepoContext(
            root=Path("/test/repo"),
            repo_name="test-repo",
            workstacks_dir=Path("/test/repo/workstacks"),
        )

        # Create a test worktree directory
        worktree_path = tmp_path / "test-worktree"
        worktree_path.mkdir()

        with pytest.raises(SystemExit) as exc_info:
            activate_worktree(repo, worktree_path, script=False, command_name="switch")

        # Should exit with code 0
        assert exc_info.value.code == 0

        # Should output instructions
        output = captured_stdout.getvalue()
        assert "Shell integration not detected" in output
        assert "source <(workstack switch test-worktree --script)" in output
    finally:
        sys.stdout = original_stdout


def test_activate_worktree_not_found() -> None:
    """Test activate_worktree exits with code 1 when worktree doesn't exist."""
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    captured_stdout = StringIO()
    captured_stderr = StringIO()

    try:
        sys.stdout = captured_stdout
        sys.stderr = captured_stderr
        repo = RepoContext(
            root=Path("/test/repo"),
            repo_name="test-repo",
            workstacks_dir=Path("/test/repo/workstacks"),
        )

        # Use a non-existent worktree path
        worktree_path = Path("/nonexistent/worktree")

        with pytest.raises(SystemExit) as exc_info:
            activate_worktree(repo, worktree_path, script=True, command_name="switch")

        # Should exit with code 1
        assert exc_info.value.code == 1

        # Should output error message to stderr
        error_output = captured_stderr.getvalue()
        assert "Worktree not found: /nonexistent/worktree" in error_output

        # Should not output anything to stdout
        assert captured_stdout.getvalue() == ""
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr


def test_finish_with_cd_script_mode(tmp_path: Path) -> None:
    """Test finish_with_cd in script mode outputs script path."""
    original_stdout = sys.stdout
    captured_stdout = StringIO()

    try:
        sys.stdout = captured_stdout

        target_path = tmp_path / "target"
        target_path.mkdir()

        with pytest.raises(SystemExit) as exc_info:
            finish_with_cd(
                target_path,
                script=True,
                command_name="create",
                success_message="Created worktree",
            )

        # Should exit with code 0
        assert exc_info.value.code == 0

        # Should output a temp file path (no newline at end)
        output = captured_stdout.getvalue()
        assert output.startswith(tempfile.gettempdir())
        assert output.endswith(".sh")
        assert not output.endswith("\n")

        # Verify the script file was created
        script_path = Path(output)
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")
        assert "cd " in script_content
        assert str(target_path) in script_content
        assert 'echo "Created worktree"' in script_content

        # Clean up
        script_path.unlink()
    finally:
        sys.stdout = original_stdout


def test_finish_with_cd_non_script_mode(tmp_path: Path) -> None:
    """Test finish_with_cd in non-script mode just exits."""
    original_stdout = sys.stdout
    captured_stdout = StringIO()

    try:
        sys.stdout = captured_stdout

        target_path = tmp_path / "target"
        target_path.mkdir()

        with pytest.raises(SystemExit) as exc_info:
            finish_with_cd(
                target_path,
                script=False,
                command_name="create",
                success_message="Created worktree",
            )

        # Should exit with code 0
        assert exc_info.value.code == 0

        # Should not output anything to stdout in non-script mode
        assert captured_stdout.getvalue() == ""
    finally:
        sys.stdout = original_stdout


def test_finish_with_activation_script_mode(tmp_path: Path) -> None:
    """Test finish_with_activation in script mode outputs script path."""
    original_stdout = sys.stdout
    captured_stdout = StringIO()

    try:
        sys.stdout = captured_stdout

        target_path = tmp_path / "target"
        target_path.mkdir()

        with pytest.raises(SystemExit) as exc_info:
            finish_with_activation(
                target_path,
                script=True,
                command_name="jump",
                final_message='echo "Jumped to worktree"',
            )

        # Should exit with code 0
        assert exc_info.value.code == 0

        # Should output a temp file path (no newline at end)
        output = captured_stdout.getvalue()
        assert output.startswith(tempfile.gettempdir())
        assert output.endswith(".sh")
        assert not output.endswith("\n")

        # Verify the script file was created
        script_path = Path(output)
        assert script_path.exists()
        script_content = script_path.read_text(encoding="utf-8")
        assert "cd " in script_content
        assert str(target_path) in script_content
        assert 'echo "Jumped to worktree"' in script_content
        # Should include venv activation
        assert ".venv" in script_content

        # Clean up
        script_path.unlink()
    finally:
        sys.stdout = original_stdout


def test_finish_with_activation_non_script_mode(tmp_path: Path) -> None:
    """Test finish_with_activation in non-script mode just exits."""
    original_stdout = sys.stdout
    captured_stdout = StringIO()

    try:
        sys.stdout = captured_stdout

        target_path = tmp_path / "target"
        target_path.mkdir()

        with pytest.raises(SystemExit) as exc_info:
            finish_with_activation(
                target_path,
                script=False,
                command_name="jump",
                final_message='echo "Jumped to worktree"',
            )

        # Should exit with code 0
        assert exc_info.value.code == 0

        # Should not output anything to stdout in non-script mode
        assert captured_stdout.getvalue() == ""
    finally:
        sys.stdout = original_stdout


def test_activate_root_repo_custom_command_name() -> None:
    """Test activate_root_repo uses custom command name in instructions."""
    original_stdout = sys.stdout
    captured_stdout = StringIO()

    try:
        sys.stdout = captured_stdout
        repo = RepoContext(
            root=Path("/test/repo"),
            repo_name="test-repo",
            workstacks_dir=Path("/test/repo/workstacks"),
        )

        with pytest.raises(SystemExit) as exc_info:
            activate_root_repo(repo, script=False, command_name="down")

        # Should exit with code 0
        assert exc_info.value.code == 0

        # Should use custom command name (not "switch") in instructions
        output = captured_stdout.getvalue()
        assert "source <(workstack down --script)" in output
        assert "source <(workstack switch root --script)" not in output
    finally:
        sys.stdout = original_stdout


def test_activate_worktree_custom_command_name(tmp_path: Path) -> None:
    """Test activate_worktree uses custom command name in instructions."""
    original_stdout = sys.stdout
    captured_stdout = StringIO()

    try:
        sys.stdout = captured_stdout
        repo = RepoContext(
            root=Path("/test/repo"),
            repo_name="test-repo",
            workstacks_dir=Path("/test/repo/workstacks"),
        )

        worktree_path = tmp_path / "test-worktree"
        worktree_path.mkdir()

        with pytest.raises(SystemExit) as exc_info:
            activate_worktree(repo, worktree_path, script=False, command_name="up")

        # Should exit with code 0
        assert exc_info.value.code == 0

        # Should use custom command name (not "switch") in instructions
        output = captured_stdout.getvalue()
        assert "source <(workstack up --script)" in output
        assert "source <(workstack switch test-worktree --script)" not in output
    finally:
        sys.stdout = original_stdout
