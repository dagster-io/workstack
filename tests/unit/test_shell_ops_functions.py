"""Unit tests for shell operations helper functions."""

from pathlib import Path

from erk.core.shell_ops import detect_shell_from_env


def test_detect_shell_from_env_zsh():
    """Test shell detection for zsh."""
    result = detect_shell_from_env("/usr/local/bin/zsh")

    assert result is not None
    shell_name, rc_file = result
    assert shell_name == "zsh"
    assert rc_file == Path.home() / ".zshrc"


def test_detect_shell_from_env_bash():
    """Test shell detection for bash."""
    result = detect_shell_from_env("/bin/bash")

    assert result is not None
    shell_name, rc_file = result
    assert shell_name == "bash"
    assert rc_file == Path.home() / ".bashrc"


def test_detect_shell_from_env_fish():
    """Test shell detection for fish."""
    result = detect_shell_from_env("/usr/bin/fish")

    assert result is not None
    shell_name, rc_file = result
    assert shell_name == "fish"
    assert rc_file == Path.home() / ".config" / "fish" / "config.fish"


def test_detect_shell_from_env_unsupported():
    """Test shell detection for unsupported shell."""
    result = detect_shell_from_env("/bin/ksh")
    assert result is None


def test_detect_shell_from_env_empty():
    """Test shell detection with empty string."""
    result = detect_shell_from_env("")
    assert result is None


def test_detect_shell_from_env_with_complex_path():
    """Test shell detection with complex path."""
    result = detect_shell_from_env("/opt/homebrew/bin/zsh")

    assert result is not None
    shell_name, rc_file = result
    assert shell_name == "zsh"
    assert rc_file == Path.home() / ".zshrc"
