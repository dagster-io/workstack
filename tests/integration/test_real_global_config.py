from pathlib import Path
from unittest import mock

import pytest

from workstack.cli.commands.create import make_env_content
from workstack.cli.commands.init import create_global_config, discover_presets
from workstack.cli.config import load_config
from workstack.core.global_config import GlobalConfig


def test_load_config_defaults(tmp_path: Path) -> None:
    cfg = load_config(tmp_path)
    assert cfg.env == {}
    assert cfg.post_create_commands == []
    assert cfg.post_create_shell is None


def test_env_rendering(tmp_path: Path) -> None:
    # Write a config
    config_dir = tmp_path / "config_dir"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        """
        [env]
        DAGSTER_GIT_REPO_DIR = "{worktree_path}"
        CUSTOM_NAME = "{name}"

        [post_create]
        shell = "bash"
        commands = ["echo hi"]
        """.strip()
    )

    cfg = load_config(config_dir)
    wt_path = tmp_path / "worktrees" / "foo"
    repo_root = tmp_path
    content = make_env_content(cfg, worktree_path=wt_path, repo_root=repo_root, name="foo")

    assert 'DAGSTER_GIT_REPO_DIR="' + str(wt_path) + '"' in content
    assert 'CUSTOM_NAME="foo"' in content
    assert 'WORKTREE_PATH="' + str(wt_path) + '"' in content
    assert 'REPO_ROOT="' + str(repo_root) + '"' in content
    assert 'WORKTREE_NAME="foo"' in content


def test_load_global_config_valid(tmp_path: Path) -> None:
    workstacks_root = tmp_path / "workstacks"
    global_config_ops = GlobalConfig(
        workstacks_root=workstacks_root,
        use_graphite=True,
        shell_setup_complete=False,
        show_pr_info=True,
        show_pr_checks=False,
    )

    assert global_config_ops.get_workstacks_root() == workstacks_root.resolve()
    assert global_config_ops.get_use_graphite() is True


def test_load_global_config_missing_file(tmp_path: Path) -> None:
    global_config_ops = GlobalConfig(
        workstacks_root=Path("/test/workstacks"),
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=True,
        show_pr_checks=False,
    )  # Config doesn't exist

    with pytest.raises(FileNotFoundError, match="Global config not found"):
        global_config_ops.get_workstacks_root()


def test_load_global_config_missing_workstacks_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Test Real implementation's validation
    from workstack.core.global_config_ops import RealGlobalConfigOps

    config_file = tmp_path / "config.toml"
    config_file.write_text("use_graphite = true\n", encoding="utf-8")

    # Override the path for Real implementation
    monkeypatch.setenv("HOME", str(tmp_path))
    real_ops = RealGlobalConfigOps()
    real_ops._path = config_file

    with pytest.raises(ValueError, match="Missing 'workstacks_root'"):
        real_ops.get_workstacks_root()


def test_load_global_config_use_graphite_defaults_false(tmp_path: Path) -> None:
    workstacks_root = tmp_path / "workstacks"
    global_config_ops = GlobalConfig(
        workstacks_root=workstacks_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=True,
        show_pr_checks=False,
    )

    assert global_config_ops.get_workstacks_root() == workstacks_root.resolve()
    assert global_config_ops.get_use_graphite() is False


def test_create_global_config_creates_file(tmp_path: Path) -> None:
    from tests.fakes.shell_ops import FakeShellOps

    global_config_ops = GlobalConfig(
        workstacks_root=Path("/test/workstacks"),
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=True,
        show_pr_checks=False,
    )

    with mock.patch("workstack.cli.commands.init.detect_graphite", return_value=False):
        create_global_config(
            global_config_ops, FakeShellOps(), Path("/tmp/workstacks"), shell_setup_complete=False
        )

    # Verify config was saved
    assert global_config_ops.get_workstacks_root() == Path("/tmp/workstacks")
    assert global_config_ops.get_use_graphite() is False


def test_create_global_config_creates_parent_directory(tmp_path: Path) -> None:
    # Test Real implementation's filesystem behavior
    from tests.fakes.shell_ops import FakeShellOps
    from workstack.core.global_config_ops import RealGlobalConfigOps

    config_file = tmp_path / ".workstack" / "config.toml"
    assert not config_file.parent.exists()

    real_ops = RealGlobalConfigOps()
    real_ops._path = config_file

    with mock.patch("workstack.cli.commands.init.detect_graphite", return_value=False):
        create_global_config(
            real_ops, FakeShellOps(), Path("/tmp/workstacks"), shell_setup_complete=False
        )

    assert config_file.parent.exists()
    assert config_file.exists()


def test_create_global_config_detects_graphite(tmp_path: Path) -> None:
    from tests.fakes.shell_ops import FakeShellOps

    global_config_ops = GlobalConfig(
        workstacks_root=Path("/test/workstacks"),
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=True,
        show_pr_checks=False,
    )

    with mock.patch("workstack.cli.commands.init.detect_graphite", return_value=True):
        create_global_config(
            global_config_ops, FakeShellOps(), Path("/tmp/workstacks"), shell_setup_complete=False
        )

    assert global_config_ops.get_use_graphite() is True


def test_discover_presets(tmp_path: Path) -> None:
    # Create structure: tmp_path/commands/init.py (mocked) and tmp_path/presets/*.toml
    commands_dir = tmp_path / "commands"
    commands_dir.mkdir()
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir()
    (presets_dir / "generic.toml").write_text("# generic preset\n", encoding="utf-8")
    (presets_dir / "dagster.toml").write_text("# dagster preset\n", encoding="utf-8")
    (presets_dir / "custom.toml").write_text("# custom preset\n", encoding="utf-8")
    (presets_dir / "README.md").write_text("# readme\n", encoding="utf-8")
    (presets_dir / "subdir").mkdir()

    with mock.patch("workstack.cli.commands.init.__file__", str(commands_dir / "init.py")):
        presets = discover_presets()

    assert presets == ["custom", "dagster", "generic"]


def test_discover_presets_missing_directory(tmp_path: Path) -> None:
    # Create structure: tmp_path/commands/init.py (mocked) but no presets directory
    commands_dir = tmp_path / "commands"
    commands_dir.mkdir()

    with mock.patch("workstack.cli.commands.init.__file__", str(commands_dir / "init.py")):
        presets = discover_presets()

    assert presets == []


def test_load_config_with_post_create_commands(tmp_path: Path) -> None:
    config_dir = tmp_path / "config_dir"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        """
        [env]
        FOO = "bar"

        [post_create]
        shell = "bash"
        commands = [
            "uv venv",
            "uv run make dev_install",
            "echo 'setup complete'"
        ]
        """.strip(),
        encoding="utf-8",
    )

    cfg = load_config(config_dir)
    assert cfg.env == {"FOO": "bar"}
    assert cfg.post_create_shell == "bash"
    assert cfg.post_create_commands == [
        "uv venv",
        "uv run make dev_install",
        "echo 'setup complete'",
    ]


def test_load_config_with_partial_post_create(tmp_path: Path) -> None:
    config_dir = tmp_path / "config_dir"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        """
        [post_create]
        commands = ["echo 'hello'"]
        """.strip(),
        encoding="utf-8",
    )

    cfg = load_config(config_dir)
    assert cfg.env == {}
    assert cfg.post_create_shell is None
    assert cfg.post_create_commands == ["echo 'hello'"]
