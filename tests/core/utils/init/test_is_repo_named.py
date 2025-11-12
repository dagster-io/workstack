"""Tests for is_repo_named function."""

from pathlib import Path

from workstack.core.init_utils import is_repo_named


def test_returns_true_for_matching_name(tmp_path: Path) -> None:
    """Test returns True when name matches."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "dagster"', encoding="utf-8")

    result = is_repo_named(tmp_path, "dagster")
    assert result is True


def test_case_insensitive_matching(tmp_path: Path) -> None:
    """Test matching is case-insensitive."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "Dagster"', encoding="utf-8")

    assert is_repo_named(tmp_path, "dagster") is True
    assert is_repo_named(tmp_path, "DAGSTER") is True
    assert is_repo_named(tmp_path, "DaGsTeR") is True


def test_returns_false_for_non_matching_name(tmp_path: Path) -> None:
    """Test returns False when name doesn't match."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "other-project"', encoding="utf-8")

    result = is_repo_named(tmp_path, "dagster")
    assert result is False


def test_returns_false_when_no_project_name(tmp_path: Path) -> None:
    """Test returns False when no project name is found."""
    result = is_repo_named(tmp_path, "dagster")
    assert result is False
