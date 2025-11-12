"""Tests for discover_presets function."""

from pathlib import Path

from workstack.core.init_utils import discover_presets


def test_discovers_preset_files(tmp_path: Path) -> None:
    """Test discovers .toml files in presets directory."""
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir()

    (presets_dir / "dagster.toml").write_text("", encoding="utf-8")
    (presets_dir / "generic.toml").write_text("", encoding="utf-8")
    (presets_dir / "python.toml").write_text("", encoding="utf-8")

    result = discover_presets(presets_dir)

    assert result == ["dagster", "generic", "python"]


def test_returns_empty_list_when_dir_missing(tmp_path: Path) -> None:
    """Test returns empty list when directory doesn't exist."""
    presets_dir = tmp_path / "nonexistent"

    result = discover_presets(presets_dir)

    assert result == []


def test_ignores_non_toml_files(tmp_path: Path) -> None:
    """Test ignores files without .toml extension."""
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir()

    (presets_dir / "dagster.toml").write_text("", encoding="utf-8")
    (presets_dir / "readme.md").write_text("", encoding="utf-8")
    (presets_dir / "notes.txt").write_text("", encoding="utf-8")

    result = discover_presets(presets_dir)

    assert result == ["dagster"]


def test_ignores_subdirectories(tmp_path: Path) -> None:
    """Test ignores subdirectories."""
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir()

    (presets_dir / "dagster.toml").write_text("", encoding="utf-8")
    subdir = presets_dir / "subdir.toml"
    subdir.mkdir()

    result = discover_presets(presets_dir)

    assert result == ["dagster"]


def test_returns_sorted_list(tmp_path: Path) -> None:
    """Test returns alphabetically sorted list."""
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir()

    # Create in non-alphabetical order
    (presets_dir / "zulu.toml").write_text("", encoding="utf-8")
    (presets_dir / "alpha.toml").write_text("", encoding="utf-8")
    (presets_dir / "bravo.toml").write_text("", encoding="utf-8")

    result = discover_presets(presets_dir)

    assert result == ["alpha", "bravo", "zulu"]
