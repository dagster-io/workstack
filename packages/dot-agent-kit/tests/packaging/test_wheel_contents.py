"""Tests for wheel packaging integrity.

Verifies that all data files are included in the built wheel package.
"""

import subprocess
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def build_wheel(tmp_path: Path) -> Path:
    """Build the wheel in a temporary directory and return wheel path."""
    # Get the package directory (dot-agent-kit)
    package_dir = Path(__file__).parent.parent.parent
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()

    # Build the wheel
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(dist_dir)],
        cwd=package_dir,
        capture_output=True,
        text=True,
        check=True,
    )

    # Find the wheel file
    wheel_files = list(dist_dir.glob("*.whl"))
    if not wheel_files:
        msg = f"No wheel file found in {dist_dir}"
        raise FileNotFoundError(msg)

    return wheel_files[0]


def test_wheel_contains_registry(build_wheel: Path) -> None:
    """Test that registry.yaml is included in the wheel."""
    with zipfile.ZipFile(build_wheel) as wheel:
        files = wheel.namelist()
        assert any("dot_agent_kit/data/registry.yaml" in f for f in files)


@pytest.mark.parametrize(
    "kit_name",
    ["gt", "devrun", "dignified-python", "workstack"],
)
def test_wheel_contains_kit_yaml(build_wheel: Path, kit_name: str) -> None:
    """Test that each kit's kit.yaml is included in the wheel."""
    with zipfile.ZipFile(build_wheel) as wheel:
        files = wheel.namelist()
        expected_path = f"dot_agent_kit/data/kits/{kit_name}/kit.yaml"
        assert any(expected_path in f for f in files), f"Missing {expected_path}"


@pytest.mark.parametrize(
    ("kit_name", "skill_name", "reference_file"),
    [
        ("gt", "gt-graphite", "gt-reference.md"),
    ],
)
def test_wheel_contains_skill_references(
    build_wheel: Path,
    kit_name: str,
    skill_name: str,
    reference_file: str,
) -> None:
    """Test that skill reference files are included in the wheel."""
    with zipfile.ZipFile(build_wheel) as wheel:
        files = wheel.namelist()
        expected_path = (
            f"dot_agent_kit/data/kits/{kit_name}/skills/{skill_name}/references/{reference_file}"
        )
        assert any(expected_path in f for f in files), f"Missing {expected_path}"


@pytest.mark.parametrize(
    ("kit_name", "skill_name"),
    [
        ("gt", "gt-graphite"),
    ],
)
def test_wheel_contains_skill_markdown(
    build_wheel: Path,
    kit_name: str,
    skill_name: str,
) -> None:
    """Test that skill SKILL.md files are included in the wheel."""
    with zipfile.ZipFile(build_wheel) as wheel:
        files = wheel.namelist()
        expected_path = f"dot_agent_kit/data/kits/{kit_name}/skills/{skill_name}/SKILL.md"
        assert any(expected_path in f for f in files), f"Missing {expected_path}"


@pytest.mark.parametrize(
    ("kit_name", "command_script"),
    [
        ("gt", "submit_branch.py"),
        ("gt", "update_pr.py"),
    ],
)
def test_wheel_contains_kit_cli_commands(
    build_wheel: Path,
    kit_name: str,
    command_script: str,
) -> None:
    """Test that kit CLI command scripts are included in the wheel."""
    with zipfile.ZipFile(build_wheel) as wheel:
        files = wheel.namelist()
        expected_path = (
            f"dot_agent_kit/data/kits/{kit_name}/kit_cli_commands/{kit_name}/{command_script}"
        )
        assert any(expected_path in f for f in files), f"Missing {expected_path}"


def test_wheel_contains_all_init_files(build_wheel: Path) -> None:
    """Test that all __init__.py files are included in data directories."""
    expected_init_files = [
        "dot_agent_kit/data/__init__.py",
        "dot_agent_kit/data/kits/__init__.py",
        "dot_agent_kit/data/kits/gt/__init__.py",
        "dot_agent_kit/data/kits/gt/commands/__init__.py",
        "dot_agent_kit/data/kits/gt/kit_cli_commands/__init__.py",
        "dot_agent_kit/data/kits/gt/skills/__init__.py",
        "dot_agent_kit/data/kits/gt/skills/gt-graphite/__init__.py",
        "dot_agent_kit/data/kits/gt/skills/gt-graphite/references/__init__.py",
        "dot_agent_kit/data/kits/devrun/__init__.py",
        "dot_agent_kit/data/kits/dignified-python/__init__.py",
        "dot_agent_kit/data/kits/workstack/__init__.py",
    ]

    with zipfile.ZipFile(build_wheel) as wheel:
        files = wheel.namelist()
        for init_file in expected_init_files:
            assert any(init_file in f for f in files), f"Missing {init_file}"
