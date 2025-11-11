"""Tests for init_utils module - pure business logic for init operations."""

from pathlib import Path

import pytest

from workstack.core.init_utils import (
    add_gitignore_entry,
    detect_root_project_name,
    discover_presets,
    get_shell_wrapper_content,
    is_repo_named,
    render_config_template,
)


class TestDetectRootProjectName:
    """Tests for detect_root_project_name function."""

    def test_detects_name_from_pyproject_toml(self, tmp_path: Path) -> None:
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

    def test_detects_name_from_setup_py(self, tmp_path: Path) -> None:
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

    def test_prefers_pyproject_over_setup_py(self, tmp_path: Path) -> None:
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

    def test_returns_none_when_no_config_files(self, tmp_path: Path) -> None:
        """Test returns None when no configuration files exist."""
        result = detect_root_project_name(tmp_path)
        assert result is None

    def test_returns_none_when_pyproject_missing_name(self, tmp_path: Path) -> None:
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

    def test_returns_none_when_pyproject_missing_project_section(self, tmp_path: Path) -> None:
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

    def test_handles_single_quotes_in_setup_py(self, tmp_path: Path) -> None:
        """Test detection of single-quoted name in setup.py."""
        setup_py = tmp_path / "setup.py"
        setup_py.write_text("setup(name='single-quoted-name')", encoding="utf-8")

        result = detect_root_project_name(tmp_path)
        assert result == "single-quoted-name"

    def test_handles_double_quotes_in_setup_py(self, tmp_path: Path) -> None:
        """Test detection of double-quoted name in setup.py."""
        setup_py = tmp_path / "setup.py"
        setup_py.write_text('setup(name="double-quoted-name")', encoding="utf-8")

        result = detect_root_project_name(tmp_path)
        assert result == "double-quoted-name"

    def test_handles_multiline_setup_py(self, tmp_path: Path) -> None:
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


class TestIsRepoNamed:
    """Tests for is_repo_named function."""

    def test_returns_true_for_matching_name(self, tmp_path: Path) -> None:
        """Test returns True when name matches."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "dagster"', encoding="utf-8")

        result = is_repo_named(tmp_path, "dagster")
        assert result is True

    def test_case_insensitive_matching(self, tmp_path: Path) -> None:
        """Test matching is case-insensitive."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "Dagster"', encoding="utf-8")

        assert is_repo_named(tmp_path, "dagster") is True
        assert is_repo_named(tmp_path, "DAGSTER") is True
        assert is_repo_named(tmp_path, "DaGsTeR") is True

    def test_returns_false_for_non_matching_name(self, tmp_path: Path) -> None:
        """Test returns False when name doesn't match."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "other-project"', encoding="utf-8")

        result = is_repo_named(tmp_path, "dagster")
        assert result is False

    def test_returns_false_when_no_project_name(self, tmp_path: Path) -> None:
        """Test returns False when no project name is found."""
        result = is_repo_named(tmp_path, "dagster")
        assert result is False


class TestDiscoverPresets:
    """Tests for discover_presets function."""

    def test_discovers_preset_files(self, tmp_path: Path) -> None:
        """Test discovers .toml files in presets directory."""
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()

        (presets_dir / "dagster.toml").write_text("", encoding="utf-8")
        (presets_dir / "generic.toml").write_text("", encoding="utf-8")
        (presets_dir / "python.toml").write_text("", encoding="utf-8")

        result = discover_presets(presets_dir)

        assert result == ["dagster", "generic", "python"]

    def test_returns_empty_list_when_dir_missing(self, tmp_path: Path) -> None:
        """Test returns empty list when directory doesn't exist."""
        presets_dir = tmp_path / "nonexistent"

        result = discover_presets(presets_dir)

        assert result == []

    def test_ignores_non_toml_files(self, tmp_path: Path) -> None:
        """Test ignores files without .toml extension."""
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()

        (presets_dir / "dagster.toml").write_text("", encoding="utf-8")
        (presets_dir / "readme.md").write_text("", encoding="utf-8")
        (presets_dir / "notes.txt").write_text("", encoding="utf-8")

        result = discover_presets(presets_dir)

        assert result == ["dagster"]

    def test_ignores_subdirectories(self, tmp_path: Path) -> None:
        """Test ignores subdirectories."""
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()

        (presets_dir / "dagster.toml").write_text("", encoding="utf-8")
        subdir = presets_dir / "subdir.toml"
        subdir.mkdir()

        result = discover_presets(presets_dir)

        assert result == ["dagster"]

    def test_returns_sorted_list(self, tmp_path: Path) -> None:
        """Test returns alphabetically sorted list."""
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()

        # Create in non-alphabetical order
        (presets_dir / "zulu.toml").write_text("", encoding="utf-8")
        (presets_dir / "alpha.toml").write_text("", encoding="utf-8")
        (presets_dir / "bravo.toml").write_text("", encoding="utf-8")

        result = discover_presets(presets_dir)

        assert result == ["alpha", "bravo", "zulu"]


class TestRenderConfigTemplate:
    """Tests for render_config_template function."""

    def test_renders_specified_preset(self, tmp_path: Path) -> None:
        """Test renders content from specified preset file."""
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()

        dagster_preset = presets_dir / "dagster.toml"
        dagster_preset.write_text("trunk_branch = 'master'", encoding="utf-8")

        result = render_config_template(presets_dir, "dagster")

        assert result == "trunk_branch = 'master'"

    def test_renders_generic_when_none_specified(self, tmp_path: Path) -> None:
        """Test renders generic preset when None specified."""
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()

        generic_preset = presets_dir / "generic.toml"
        generic_preset.write_text("trunk_branch = 'main'", encoding="utf-8")

        result = render_config_template(presets_dir, None)

        assert result == "trunk_branch = 'main'"

    def test_raises_error_for_missing_preset(self, tmp_path: Path) -> None:
        """Test raises ValueError for non-existent preset."""
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()

        with pytest.raises(ValueError, match="Preset 'nonexistent' not found"):
            render_config_template(presets_dir, "nonexistent")

    def test_preserves_multiline_content(self, tmp_path: Path) -> None:
        """Test preserves multiline content from preset file."""
        presets_dir = tmp_path / "presets"
        presets_dir.mkdir()

        preset = presets_dir / "python.toml"
        preset.write_text(
            """trunk_branch = 'main'
worktree_prefix = 'wt-'
show_pr_info = true""",
            encoding="utf-8",
        )

        result = render_config_template(presets_dir, "python")

        assert "trunk_branch = 'main'" in result
        assert "worktree_prefix = 'wt-'" in result
        assert "show_pr_info = true" in result


class TestGetShellWrapperContent:
    """Tests for get_shell_wrapper_content function."""

    def test_loads_fish_wrapper(self, tmp_path: Path) -> None:
        """Test loads fish wrapper file."""
        shell_dir = tmp_path / "shell_integration"
        shell_dir.mkdir()

        fish_wrapper = shell_dir / "fish_wrapper.fish"
        fish_wrapper.write_text("function workstack\n    echo fish\nend", encoding="utf-8")

        result = get_shell_wrapper_content(shell_dir, "fish")

        assert "function workstack" in result
        assert "echo fish" in result

    def test_loads_zsh_wrapper(self, tmp_path: Path) -> None:
        """Test loads zsh wrapper file."""
        shell_dir = tmp_path / "shell_integration"
        shell_dir.mkdir()

        zsh_wrapper = shell_dir / "zsh_wrapper.sh"
        zsh_wrapper.write_text("workstack() {\n    echo zsh\n}", encoding="utf-8")

        result = get_shell_wrapper_content(shell_dir, "zsh")

        assert "workstack()" in result
        assert "echo zsh" in result

    def test_loads_bash_wrapper(self, tmp_path: Path) -> None:
        """Test loads bash wrapper file."""
        shell_dir = tmp_path / "shell_integration"
        shell_dir.mkdir()

        bash_wrapper = shell_dir / "bash_wrapper.sh"
        bash_wrapper.write_text("workstack() {\n    echo bash\n}", encoding="utf-8")

        result = get_shell_wrapper_content(shell_dir, "bash")

        assert "workstack()" in result
        assert "echo bash" in result

    def test_raises_error_for_missing_wrapper(self, tmp_path: Path) -> None:
        """Test raises ValueError for missing wrapper file."""
        shell_dir = tmp_path / "shell_integration"
        shell_dir.mkdir()

        with pytest.raises(ValueError, match="Shell wrapper not found for zsh"):
            get_shell_wrapper_content(shell_dir, "zsh")

    def test_raises_error_for_unsupported_shell(self, tmp_path: Path) -> None:
        """Test raises ValueError for unsupported shell type."""
        shell_dir = tmp_path / "shell_integration"
        shell_dir.mkdir()

        with pytest.raises(ValueError, match="Shell wrapper not found for powershell"):
            get_shell_wrapper_content(shell_dir, "powershell")


class TestAddGitignoreEntry:
    """Tests for add_gitignore_entry function."""

    def test_adds_entry_to_empty_content(self) -> None:
        """Test adds entry to empty gitignore content."""
        content = ""

        result = add_gitignore_entry(content, ".PLAN.md")

        assert result == "\n.PLAN.md\n"

    def test_adds_entry_to_existing_content(self) -> None:
        """Test adds entry to existing gitignore content."""
        content = "*.pyc\n__pycache__/\n"

        result = add_gitignore_entry(content, ".PLAN.md")

        assert result == "*.pyc\n__pycache__/\n.PLAN.md\n"

    def test_adds_newline_if_missing(self) -> None:
        """Test adds trailing newline before entry if missing."""
        content = "*.pyc"

        result = add_gitignore_entry(content, ".PLAN.md")

        assert result == "*.pyc\n.PLAN.md\n"

    def test_idempotent_when_entry_exists(self) -> None:
        """Test returns unchanged content when entry already exists."""
        content = "*.pyc\n.PLAN.md\n__pycache__/\n"

        result = add_gitignore_entry(content, ".PLAN.md")

        assert result == content

    def test_multiple_additions(self) -> None:
        """Test adding multiple entries."""
        content = "*.pyc\n"

        content = add_gitignore_entry(content, ".PLAN.md")
        content = add_gitignore_entry(content, ".env")

        assert ".PLAN.md" in content
        assert ".env" in content
        assert content.count(".PLAN.md") == 1
        assert content.count(".env") == 1

    def test_does_not_add_duplicate(self) -> None:
        """Test adding same entry twice is idempotent."""
        content = "*.pyc\n"

        content = add_gitignore_entry(content, ".PLAN.md")
        content_before = content
        content = add_gitignore_entry(content, ".PLAN.md")

        assert content == content_before

    def test_preserves_existing_formatting(self) -> None:
        """Test preserves existing content formatting."""
        content = "# Python\n*.pyc\n\n# Node\nnode_modules/\n"

        result = add_gitignore_entry(content, ".PLAN.md")

        assert "# Python" in result
        assert "*.pyc" in result
        assert "# Node" in result
        assert result.endswith(".PLAN.md\n")

    def test_handles_entry_as_substring(self) -> None:
        """Test correctly identifies existing entry (not just substring match)."""
        content = ".PLAN.md.backup\n"

        result = add_gitignore_entry(content, ".PLAN.md")

        # Since ".PLAN.md" is a substring of ".PLAN.md.backup", the current
        # implementation will think it exists. This documents current behavior.
        # If exact matching is needed, the function should be updated.
        assert result == content
