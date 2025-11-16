from pathlib import Path

from erk.core.init_utils import detect_root_project_name, is_repo_named


def test_detects_by_root_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='dagster'\n")
    assert is_repo_named(tmp_path, "dagster")
    assert detect_root_project_name(tmp_path) == "dagster"


def test_detects_by_setup_py(tmp_path: Path) -> None:
    (tmp_path / "setup.py").write_text("setup(name='dagster')")
    assert is_repo_named(tmp_path, "dagster")
    assert detect_root_project_name(tmp_path) == "dagster"


def test_negative(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='not-dagster'\n")
    assert not is_repo_named(tmp_path, "dagster")
    assert detect_root_project_name(tmp_path) == "not-dagster"
