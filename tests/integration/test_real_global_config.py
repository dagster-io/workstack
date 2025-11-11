from pathlib import Path
from unittest import mock

import pytest

from tests.fakes.shell_ops import FakeShellOps
from workstack.cli.commands.create import make_env_content
from workstack.cli.commands.init import create_and_save_global_config
from workstack.cli.config import load_config
from workstack.core.init_utils import discover_presets


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


# NOTE: Tests removed during FakeGlobalConfigOps deprecation (Phase 3a)
# These tests were testing the FakeGlobalConfigOps interface which has been
# removed. If these behaviors need coverage, they should be tested via
# RealGlobalConfigOps or GlobalConfig directly.

# def test_load_global_config_valid(tmp_path: Path) -> None:
#     ... (removed - was testing FakeGlobalConfigOps)

# def test_load_global_config_missing_file(tmp_path: Path) -> None:
#     ... (removed - was testing FakeGlobalConfigOps)


def test_load_global_config_missing_workstacks_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Test that FilesystemGlobalConfigOps validates required fields
    from workstack.core.global_config import FilesystemGlobalConfigOps

    config_file = tmp_path / "config.toml"
    config_file.write_text("use_graphite = true\n", encoding="utf-8")

    # Patch Path.home to return tmp_path so ops looks in tmp_path/.workstack/
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    # Create .workstack dir and write config there
    workstack_dir = tmp_path / ".workstack"
    workstack_dir.mkdir()
    (workstack_dir / "config.toml").write_text("use_graphite = true\n", encoding="utf-8")

    ops = FilesystemGlobalConfigOps()
    with pytest.raises(ValueError, match="Missing 'workstacks_root'"):
        ops.load()


# def test_load_global_config_use_graphite_defaults_false(tmp_path: Path) -> None:
#     ... (removed - was testing FakeGlobalConfigOps)

# def test_create_global_config_creates_file(tmp_path: Path) -> None:
#     ... (removed - was testing FakeGlobalConfigOps)


def test_create_global_config_creates_parent_directory(tmp_path: Path) -> None:
    # Test that create_and_save_global_config creates parent directory
    from workstack.core.context import WorkstackContext
    from workstack.core.global_config import InMemoryGlobalConfigOps

    config_file = tmp_path / ".workstack" / "config.toml"
    assert not config_file.parent.exists()

    # Create test context with InMemoryGlobalConfigOps
    global_config_ops = InMemoryGlobalConfigOps(config=None)
    ctx = WorkstackContext.for_test(
        shell_ops=FakeShellOps(),
        global_config_ops=global_config_ops,
        global_config=None,
        cwd=tmp_path,
    )

    with (
        mock.patch("workstack.cli.commands.init.detect_graphite", return_value=False),
        mock.patch("workstack.core.global_config.Path.home", return_value=tmp_path),
    ):
        create_and_save_global_config(ctx, Path("/tmp/workstacks"), shell_setup_complete=False)

    # Verify config was saved to in-memory ops
    assert global_config_ops.exists()
    loaded = global_config_ops.load()
    assert loaded.workstacks_root == Path("/tmp/workstacks")


# def test_create_global_config_detects_graphite(tmp_path: Path) -> None:
#     ... (removed - was testing FakeGlobalConfigOps)


def test_discover_presets(tmp_path: Path) -> None:
    # Create structure: tmp_path/presets/*.toml
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir()
    (presets_dir / "generic.toml").write_text("# generic preset\n", encoding="utf-8")
    (presets_dir / "dagster.toml").write_text("# dagster preset\n", encoding="utf-8")
    (presets_dir / "custom.toml").write_text("# custom preset\n", encoding="utf-8")
    (presets_dir / "README.md").write_text("# readme\n", encoding="utf-8")
    (presets_dir / "subdir").mkdir()

    presets = discover_presets(presets_dir)

    assert presets == ["custom", "dagster", "generic"]


def test_discover_presets_missing_directory(tmp_path: Path) -> None:
    # Test with non-existent presets directory
    presets_dir = tmp_path / "nonexistent"

    presets = discover_presets(presets_dir)

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
