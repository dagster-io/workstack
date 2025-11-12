"""Tests for get_shell_wrapper_content function."""

from pathlib import Path

import pytest

from workstack.core.init_utils import get_shell_wrapper_content


def test_loads_fish_wrapper(tmp_path: Path) -> None:
    """Test loads fish wrapper file."""
    shell_dir = tmp_path / "shell_integration"
    shell_dir.mkdir()

    fish_wrapper = shell_dir / "fish_wrapper.fish"
    fish_wrapper.write_text("function workstack\n    echo fish\nend", encoding="utf-8")

    result = get_shell_wrapper_content(shell_dir, "fish")

    assert "function workstack" in result
    assert "echo fish" in result


def test_loads_zsh_wrapper(tmp_path: Path) -> None:
    """Test loads zsh wrapper file."""
    shell_dir = tmp_path / "shell_integration"
    shell_dir.mkdir()

    zsh_wrapper = shell_dir / "zsh_wrapper.sh"
    zsh_wrapper.write_text("workstack() {\n    echo zsh\n}", encoding="utf-8")

    result = get_shell_wrapper_content(shell_dir, "zsh")

    assert "workstack()" in result
    assert "echo zsh" in result


def test_loads_bash_wrapper(tmp_path: Path) -> None:
    """Test loads bash wrapper file."""
    shell_dir = tmp_path / "shell_integration"
    shell_dir.mkdir()

    bash_wrapper = shell_dir / "bash_wrapper.sh"
    bash_wrapper.write_text("workstack() {\n    echo bash\n}", encoding="utf-8")

    result = get_shell_wrapper_content(shell_dir, "bash")

    assert "workstack()" in result
    assert "echo bash" in result


def test_raises_error_for_missing_wrapper(tmp_path: Path) -> None:
    """Test raises ValueError for missing wrapper file."""
    shell_dir = tmp_path / "shell_integration"
    shell_dir.mkdir()

    with pytest.raises(ValueError, match="Shell wrapper not found for zsh"):
        get_shell_wrapper_content(shell_dir, "zsh")


def test_raises_error_for_unsupported_shell(tmp_path: Path) -> None:
    """Test raises ValueError for unsupported shell type."""
    shell_dir = tmp_path / "shell_integration"
    shell_dir.mkdir()

    with pytest.raises(ValueError, match="Shell wrapper not found for powershell"):
        get_shell_wrapper_content(shell_dir, "powershell")
