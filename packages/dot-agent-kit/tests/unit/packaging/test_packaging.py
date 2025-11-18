"""Tests for package utilities."""

from pathlib import Path

from dot_agent_kit.utils import (
    find_kit_manifest,
    get_package_path,
    get_package_version,
    is_package_installed,
)


def test_is_package_installed() -> None:
    """Test package installation detection."""
    assert is_package_installed("click") is True
    assert is_package_installed("nonexistent_package") is False


def test_get_package_version() -> None:
    """Test package version extraction."""
    version_str = get_package_version("click")
    assert version_str is not None
    assert version_str.count(".") >= 1  # At least major.minor


def test_get_package_version_not_installed() -> None:
    """Test version of non-existent package."""
    assert get_package_version("nonexistent_package") is None


def test_get_package_path() -> None:
    """Test getting package filesystem path."""
    path = get_package_path("click")
    assert path is not None
    assert path.exists()
    assert path.is_dir()


def test_get_package_path_not_installed() -> None:
    """Test path of non-existent package."""
    assert get_package_path("nonexistent_package") is None


def test_find_kit_manifest(tmp_path: Path) -> None:
    """Test finding kit.yaml in package."""
    package_dir = tmp_path / "test_package"
    package_dir.mkdir()

    manifest_path = package_dir / "kit.yaml"
    manifest_path.write_text("name: test\nversion: 1.0.0\n", encoding="utf-8")

    found = find_kit_manifest(package_dir)
    assert found == manifest_path


def test_find_kit_manifest_parent(tmp_path: Path) -> None:
    """Test finding kit.yaml in parent directory."""
    package_dir = tmp_path / "test_package"
    package_dir.mkdir()

    # Put manifest in parent directory
    manifest_path = tmp_path / "kit.yaml"
    manifest_path.write_text("name: test\nversion: 1.0.0\n", encoding="utf-8")

    found = find_kit_manifest(package_dir)
    assert found == manifest_path


def test_find_kit_manifest_not_found(tmp_path: Path) -> None:
    """Test when kit.yaml doesn't exist."""
    package_dir = tmp_path / "test_package"
    package_dir.mkdir()

    assert find_kit_manifest(package_dir) is None
