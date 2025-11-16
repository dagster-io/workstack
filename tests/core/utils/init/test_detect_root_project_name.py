"""Tests for detect_root_project_name function."""

from pathlib import Path

from erk.core.init_utils import detect_root_project_name


def test_detects_name_from_pyproject_toml(tmp_path: Path) -> None:
    """Test detection from pyproject.toml."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "my-project"
version = "1.0.0"
""",
        encoding="utf-8",
    )

    result = detect_root_project_name(tmp_path)
    assert result == "my-project"


def test_detects_name_from_setup_py(tmp_path: Path) -> None:
    """Test detection from setup.py when pyproject.toml absent."""
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(
        """
from setuptools import setup

setup(
    name="my-setup-project",
    version="1.0.0",
)
""",
        encoding="utf-8",
    )

    result = detect_root_project_name(tmp_path)
    assert result == "my-setup-project"


def test_prefers_pyproject_over_setup_py(tmp_path: Path) -> None:
    """Test that pyproject.toml takes precedence over setup.py."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "pyproject-name"
""",
        encoding="utf-8",
    )

    setup_py = tmp_path / "setup.py"
    setup_py.write_text('setup(name="setup-name")', encoding="utf-8")

    result = detect_root_project_name(tmp_path)
    assert result == "pyproject-name"


def test_returns_none_when_no_config_files(tmp_path: Path) -> None:
    """Test returns None when no configuration files exist."""
    result = detect_root_project_name(tmp_path)
    assert result is None


def test_returns_none_when_pyproject_missing_name(tmp_path: Path) -> None:
    """Test returns None when pyproject.toml exists but has no name."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
version = "1.0.0"
""",
        encoding="utf-8",
    )

    result = detect_root_project_name(tmp_path)
    assert result is None


def test_returns_none_when_pyproject_missing_project_section(tmp_path: Path) -> None:
    """Test returns None when pyproject.toml has no [project] section."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[build-system]
requires = ["setuptools"]
""",
        encoding="utf-8",
    )

    result = detect_root_project_name(tmp_path)
    assert result is None


def test_handles_single_quotes_in_setup_py(tmp_path: Path) -> None:
    """Test detection of single-quoted name in setup.py."""
    setup_py = tmp_path / "setup.py"
    setup_py.write_text("setup(name='single-quoted-name')", encoding="utf-8")

    result = detect_root_project_name(tmp_path)
    assert result == "single-quoted-name"


def test_handles_double_quotes_in_setup_py(tmp_path: Path) -> None:
    """Test detection of double-quoted name in setup.py."""
    setup_py = tmp_path / "setup.py"
    setup_py.write_text('setup(name="double-quoted-name")', encoding="utf-8")

    result = detect_root_project_name(tmp_path)
    assert result == "double-quoted-name"


def test_handles_multiline_setup_py(tmp_path: Path) -> None:
    """Test detection in multiline setup.py."""
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(
        """
setup(
    name = "multiline-project",
    version = "1.0.0",
    author = "Someone",
)
""",
        encoding="utf-8",
    )

    result = detect_root_project_name(tmp_path)
    assert result == "multiline-project"
