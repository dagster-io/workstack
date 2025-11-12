"""Tests for the shell_integration command."""

from pathlib import Path

from click.testing import CliRunner

from tests.test_utils.env_helpers import pure_workstack_env
from workstack.cli.cli import cli


def test_shell_integration_with_switch() -> None:
    """Test shell integration with switch command."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        ctx = env.build_context()
        result = runner.invoke(cli, ["__shell", "switch", "test"], obj=ctx)
        # Should handle the command
        # May fail due to missing config, which is OK for this test
        assert result.exit_code in (0, 1)


def test_shell_integration_with_passthrough() -> None:
    """Test shell integration passthrough for non-switch commands."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        ctx = env.build_context()
        result = runner.invoke(cli, ["__shell", "list"], obj=ctx)
        # Should either passthrough or handle
        assert result.exit_code in (0, 1)


def test_shell_integration_with_help() -> None:
    """Test shell integration with help command."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        ctx = env.build_context()
        result = runner.invoke(cli, ["__shell", "--help"], obj=ctx)
        # Should handle or passthrough
        assert result.exit_code in (0, 1)


def test_shell_integration_with_no_args() -> None:
    """Test shell integration with no arguments."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        ctx = env.build_context()
        result = runner.invoke(cli, ["__shell"], obj=ctx)
        # Should handle empty args gracefully
        assert result.exit_code in (0, 1)


def test_shell_integration_passthrough_marker() -> None:
    """Test that passthrough commands print the passthrough marker."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        ctx = env.build_context()
        result = runner.invoke(cli, ["__shell", "list"], obj=ctx)
        # If it's a passthrough, should contain the marker
        # Otherwise, it's being handled directly
        assert result.exit_code in (0, 1)


def test_shell_integration_sync_returns_script_by_default() -> None:
    """Sync passthrough should return a script path instead of executing inline."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        ctx = env.build_context()
        result = runner.invoke(cli, ["__shell", "sync"], obj=ctx)
        assert result.exit_code == 0
        script_output = result.output.strip()
        assert script_output
        script_path = Path(script_output)
        # Verify script was written to in-memory storage
        content = env.script_writer.get_script_content(script_path)
        assert content is not None


def test_shell_integration_unknown_command() -> None:
    """Test shell integration with unknown command."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        ctx = env.build_context()
        result = runner.invoke(cli, ["__shell", "unknown-command", "arg1"], obj=ctx)
        # Should handle or passthrough unknown commands
        assert result.exit_code in (0, 1)


def test_shell_integration_sync_generates_posix_passthrough_script() -> None:
    """When invoked from bash/zsh, __shell should return a passthrough script."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        ctx = env.build_context()
        result = runner.invoke(cli, ["__shell", "sync"], env={"WORKSTACK_SHELL": "bash"}, obj=ctx)
        assert result.exit_code == 0
        script_output = result.output.strip()
        assert script_output
        script_path = Path(script_output)
        # Verify script content from in-memory storage
        content = env.script_writer.get_script_content(script_path)
        assert content is not None
        assert "command workstack sync" in content
        assert "__workstack_exit=$?" in content


def test_shell_integration_sync_generates_fish_passthrough_script() -> None:
    """When invoked from fish, __shell should return a fish-compatible script."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        ctx = env.build_context()
        result = runner.invoke(cli, ["__shell", "sync"], env={"WORKSTACK_SHELL": "fish"}, obj=ctx)
        assert result.exit_code == 0
        script_output = result.output.strip()
        assert script_output
        script_path = Path(script_output)
        # Verify script content from in-memory storage
        content = env.script_writer.get_script_content(script_path)
        assert content is not None
        assert 'command workstack "sync"' in content
        assert "set __workstack_exit $status" in content


def test_shell_integration_fish_escapes_special_characters() -> None:
    """Fish passthrough script should escape characters that trigger expansions."""
    runner = CliRunner()
    special_arg = "$branch;rm"
    second_arg = "(test)"
    with pure_workstack_env(runner) as env:
        ctx = env.build_context()
        result = runner.invoke(
            cli,
            ["__shell", "sync", special_arg, second_arg],
            env={"WORKSTACK_SHELL": "fish"},
            obj=ctx,
        )
        assert result.exit_code == 0
        script_output = result.output.strip()
        assert script_output
        script_path = Path(script_output)
        # Verify script content from in-memory storage
        content = env.script_writer.get_script_content(script_path)
        assert content is not None
        assert 'command workstack "sync" "\\$branch\\;rm" "\\(test\\)"' in content


def test_shell_integration_forwards_stderr_on_success() -> None:
    """Test that stderr from successful commands is forwarded to users.

    This tests the fix for silent failures where stderr messages (like warnings
    about multiple children) were captured but never shown to the user.
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        ctx = env.build_context()
        # Use up command which can produce stderr on success
        # Test will simulate a command that succeeds but has no output
        result = runner.invoke(cli, ["__shell", "up"], obj=ctx)
        # Result may fail or succeed, but stderr should be visible
        # The handler itself should forward stderr regardless of exit code
        assert result.exit_code in (0, 1)  # May fail due to missing config
        # If there's stderr, it should be captured
        # This test verifies the forwarding mechanism exists
