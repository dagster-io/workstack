"""Tests for the config command."""

from pathlib import Path

from click.testing import CliRunner

from tests.fakes.gitops import FakeGitOps
from tests.test_utils.env_helpers import simulated_workstack_env
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.global_config import GlobalConfig


def test_config_list_displays_global_config() -> None:
    """Test that config list displays global configuration."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Global configuration:" in result.output
        assert "workstacks_root=" in result.output
        assert "use_graphite=true" in result.output
        assert "show_pr_info=true" in result.output
        assert "show_pr_checks=false" in result.output


def test_config_list_displays_repo_config() -> None:
    """Test that config list displays repository configuration."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        # Create a config.toml with env vars
        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text(
            '[env]\nFOO = "bar"\n\n[post_create]\nshell = "/bin/bash"\ncommands = ["echo hello"]\n',
            encoding="utf-8",
        )

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Repository configuration:" in result.output
        assert "env.FOO=bar" in result.output
        assert "post_create.shell=/bin/bash" in result.output
        assert "post_create.commands=" in result.output


def test_config_list_handles_missing_global_config() -> None:
    """Test that config list handles missing global config gracefully."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=Path("/fake/workstacks"),
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Global configuration:" in result.output
        assert "not configured" in result.output


def test_config_list_handles_missing_repo_config() -> None:
    """Test that config list handles missing repo config gracefully."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Repository configuration:" in result.output


def test_config_list_not_in_git_repo() -> None:
    """Test that config list handles not being in a git repo."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # No .git directory

        git_ops = FakeGitOps()
        global_config_ops = GlobalConfig(
            workstacks_root=Path("/fake/workstacks"),
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "not in a git repository" in result.output


def test_config_get_workstacks_root() -> None:
    """Test getting workstacks_root config value."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "my-workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "get", "workstacks_root"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert str(workstacks_root) in result.output


def test_config_get_use_graphite() -> None:
    """Test getting use_graphite config value."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "get", "use_graphite"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "true" in result.output.strip()


def test_config_get_show_pr_info() -> None:
    """Test getting show_pr_info config value."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=False,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "get", "show_pr_info"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "false" in result.output.strip()


def test_config_get_show_pr_checks() -> None:
    """Test getting show_pr_checks config value."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "get", "show_pr_checks"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "true" in result.output.strip()


def test_config_get_global_key_missing_config_fails() -> None:
    """Test that getting global key fails when config doesn't exist."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=Path("/fake/workstacks"),
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "get", "workstacks_root"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Global config not found" in result.output


def test_config_get_env_key() -> None:
    """Test getting env.* config value."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        # Create config.toml with env var
        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text('[env]\nMY_VAR = "my_value"\n', encoding="utf-8")

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "get", "env.MY_VAR"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "my_value" in result.output.strip()


def test_config_get_post_create_shell() -> None:
    """Test getting post_create.shell config value."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        # Create config.toml with post_create.shell
        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text('[post_create]\nshell = "/bin/zsh"\n', encoding="utf-8")

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "get", "post_create.shell"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "/bin/zsh" in result.output.strip()


def test_config_get_post_create_commands() -> None:
    """Test getting post_create.commands config value."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        # Create config.toml with post_create.commands
        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text(
            '[post_create]\ncommands = ["echo hello", "echo world"]\n',
            encoding="utf-8",
        )

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "get", "post_create.commands"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "echo hello" in result.output
        assert "echo world" in result.output


def test_config_get_env_key_not_found() -> None:
    """Test that getting non-existent env key fails."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        # Create empty config.toml
        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "get", "env.NONEXISTENT"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Key not found" in result.output


def test_config_get_invalid_key_format() -> None:
    """Test that invalid key format fails."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "get", "env"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Invalid key" in result.output


def test_config_set_workstacks_root() -> None:
    """Test setting workstacks_root config value."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        new_root = env.cwd / "new-workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(
            cli, ["config", "set", "workstacks_root", str(new_root)], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        assert "Set workstacks_root=" in result.output
        assert global_config_ops.get_workstacks_root() == new_root.resolve()


def test_config_set_use_graphite_true() -> None:
    """Test setting use_graphite to true."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "set", "use_graphite", "true"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Set use_graphite=true" in result.output
        assert global_config_ops.get_use_graphite()


def test_config_set_use_graphite_false() -> None:
    """Test setting use_graphite to false."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "set", "use_graphite", "false"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Set use_graphite=false" in result.output
        assert not global_config_ops.get_use_graphite()


def test_config_set_show_pr_info() -> None:
    """Test setting show_pr_info config value."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "set", "show_pr_info", "false"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Set show_pr_info=false" in result.output
        assert not global_config_ops.get_show_pr_info()


def test_config_set_show_pr_checks() -> None:
    """Test setting show_pr_checks config value."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "set", "show_pr_checks", "true"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Set show_pr_checks=true" in result.output
        assert global_config_ops.get_show_pr_checks()


def test_config_set_invalid_boolean_fails() -> None:
    """Test that setting invalid boolean value fails."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "set", "use_graphite", "maybe"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Invalid boolean value" in result.output


def test_config_set_without_global_config_fails() -> None:
    """Test that setting config fails when global config doesn't exist."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=Path("/fake/workstacks"),
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "set", "use_graphite", "true"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Global config not found" in result.output
        assert "Run 'workstack init'" in result.output


def test_config_get_invalid_key() -> None:
    """Test that getting invalid key fails."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        # Create empty config
        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "get", "invalid_key"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Invalid key" in result.output


def test_config_set_repo_keys_not_implemented() -> None:
    """Test that setting repo keys is not yet implemented."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "set", "env.MY_VAR", "value"], obj=test_ctx)

        assert result.exit_code == 1
        assert "not yet implemented" in result.output


def test_config_key_with_multiple_dots() -> None:
    """Test that keys with multiple dots are handled."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        # Create empty config
        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["config", "get", "env.FOO.BAR"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Invalid key" in result.output
