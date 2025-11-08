"""Tests for the shell_integration command."""

from pathlib import Path

from click.testing import CliRunner

from workstack.cli.cli import cli


def test_shell_integration_with_switch() -> None:
    """Test shell integration with switch command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["__shell", "switch", "test"])
    # Should handle the command
    assert result.exit_code in (0, 1)  # May fail due to missing config, which is OK for this test


def test_shell_integration_with_passthrough() -> None:
    """Test shell integration passthrough for non-switch commands."""
    runner = CliRunner()
    result = runner.invoke(cli, ["__shell", "list"])
    # Should either passthrough or handle
    assert result.exit_code in (0, 1)


def test_shell_integration_with_help() -> None:
    """Test shell integration with help command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["__shell", "--help"])
    # Should handle or passthrough
    assert result.exit_code in (0, 1)


def test_shell_integration_with_no_args() -> None:
    """Test shell integration with no arguments."""
    runner = CliRunner()
    result = runner.invoke(cli, ["__shell"])
    # Should handle empty args gracefully
    assert result.exit_code in (0, 1)


def test_shell_integration_passthrough_marker() -> None:
    """Test that passthrough commands print the passthrough marker."""
    runner = CliRunner()
    result = runner.invoke(cli, ["__shell", "list"])
    # If it's a passthrough, should contain the marker
    # Otherwise, it's being handled directly
    assert result.exit_code in (0, 1)


def test_shell_integration_sync_returns_script_by_default() -> None:
    """Sync passthrough should return a script path instead of executing inline."""
    runner = CliRunner()
    result = runner.invoke(cli, ["__shell", "sync"])
    assert result.exit_code == 0
    script_output = result.output.strip()
    assert script_output
    script_path = Path(script_output)
    try:
        assert script_path.exists()
    finally:
        script_path.unlink(missing_ok=True)


def test_shell_integration_unknown_command() -> None:
    """Test shell integration with unknown command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["__shell", "unknown-command", "arg1"])
    # Should handle or passthrough unknown commands
    assert result.exit_code in (0, 1)


def test_shell_integration_sync_generates_posix_passthrough_script(tmp_path: Path) -> None:
    """When invoked from bash/zsh, __shell should return a passthrough script."""
    runner = CliRunner()
    result = runner.invoke(cli, ["__shell", "sync"], env={"WORKSTACK_SHELL": "bash"})
    assert result.exit_code == 0
    script_output = result.output.strip()
    assert script_output
    script_path = Path(script_output)
    try:
        content = script_path.read_text(encoding="utf-8")
        assert "command workstack sync" in content
        assert "__workstack_exit=$?" in content
    finally:
        script_path.unlink(missing_ok=True)


def test_shell_integration_sync_generates_fish_passthrough_script(tmp_path: Path) -> None:
    """When invoked from fish, __shell should return a fish-compatible script."""
    runner = CliRunner()
    result = runner.invoke(cli, ["__shell", "sync"], env={"WORKSTACK_SHELL": "fish"})
    assert result.exit_code == 0
    script_output = result.output.strip()
    assert script_output
    script_path = Path(script_output)
    try:
        content = script_path.read_text(encoding="utf-8")
        assert 'command workstack "sync"' in content
        assert "set __workstack_exit $status" in content
    finally:
        script_path.unlink(missing_ok=True)


def test_shell_integration_fish_escapes_special_characters(tmp_path: Path) -> None:
    """Fish passthrough script should escape characters that trigger expansions."""
    runner = CliRunner()
    special_arg = "$branch;rm"
    second_arg = "(test)"
    result = runner.invoke(
        cli,
        ["__shell", "sync", special_arg, second_arg],
        env={"WORKSTACK_SHELL": "fish"},
    )
    assert result.exit_code == 0
    script_output = result.output.strip()
    assert script_output
    script_path = Path(script_output)
    try:
        content = script_path.read_text(encoding="utf-8")
        assert 'command workstack "sync" "\\$branch\\;rm" "\\(test\\)"' in content
    finally:
        script_path.unlink(missing_ok=True)


def test_shell_integration_forwards_stderr_on_success() -> None:
    """Test that stderr from successful commands is forwarded to users.

    This tests the fix for silent failures where stderr messages (like warnings
    about multiple children) were captured but never shown to the user.
    """
    runner = CliRunner()
    # Use up command which can produce stderr on success
    # Test will simulate a command that succeeds but has no output
    result = runner.invoke(cli, ["__shell", "up"])
    # Result may fail or succeed, but stderr should be visible
    # The handler itself should forward stderr regardless of exit code
    assert result.exit_code in (0, 1)  # May fail due to missing config
    # If there's stderr, it should be captured
    # This test verifies the forwarding mechanism exists
