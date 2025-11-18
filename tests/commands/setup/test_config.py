"""Tests for the config command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.config import LoadedConfig
from erk.core.context import ErkContext
from erk.core.global_config import GlobalConfig
from erk.core.repo_discovery import RepoContext
from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.test_utils.env_helpers import erk_inmem_env


def test_config_list_displays_global_config() -> None:
    """Test that config list displays global configuration."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        repo_dir = env.erk_root / "repos" / env.cwd.name
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            use_graphite=True,
            git_ops=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Global configuration:" in result.output
        assert "erk_root=" in result.output
        assert "use_graphite=true" in result.output
        assert "show_pr_info=true" in result.output


def test_config_list_displays_repo_config() -> None:
    """Test that config list displays repository configuration."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        # Pass local config directly instead of creating files
        local_config = LoadedConfig(
            env={"FOO": "bar"},
            post_create_commands=["echo hello"],
            post_create_shell="/bin/bash",
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            local_config=local_config,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Repository configuration:" in result.output
        assert "env.FOO=bar" in result.output
        assert "post_create.shell=/bin/bash" in result.output
        assert "post_create.commands=" in result.output


def test_config_list_handles_missing_repo_config() -> None:
    """Test that config list handles missing repo config gracefully."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        repo_dir = env.erk_root / "repos" / env.cwd.name
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Repository configuration:" in result.output


def test_config_list_not_in_git_repo() -> None:
    """Test that config list handles not being in a git repo."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # No .git directory - empty FakeGitOps means no git repos
        git_ops = FakeGitOps()

        # Build context manually without env.build_context() to avoid auto-adding git_common_dirs
        global_config = GlobalConfig(
            erk_root=Path("/fake/erks"),
            use_graphite=False,
            show_pr_info=True,
            shell_setup_complete=False,
        )

        test_ctx = ErkContext.for_test(
            git_ops=git_ops,
            graphite_ops=FakeGraphiteOps(),
            github_ops=FakeGitHubOps(),
            global_config=global_config,
            script_writer=env.script_writer,
            cwd=env.cwd,
            repo=None,
        )

        result = runner.invoke(cli, ["config", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "not in a git repository" in result.output


def test_config_get_erk_root() -> None:
    """Test getting erk_root config value."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        repo_dir = env.erk_root / "repos" / env.cwd.name
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            repo=repo,
        )

        result = runner.invoke(cli, ["config", "get", "erk_root"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert str(env.erk_root) in result.output


def test_config_get_use_graphite() -> None:
    """Test getting use_graphite config value."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        repo_dir = env.erk_root / "repos" / env.cwd.name
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            use_graphite=True,
            git_ops=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "use_graphite"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "true" in result.output.strip()


def test_config_get_show_pr_info() -> None:
    """Test getting show_pr_info config value."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        test_ctx = env.build_context(
            git_ops=git_ops,
        )

        result = runner.invoke(cli, ["config", "get", "show_pr_info"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "true" in result.output.strip()


def test_config_get_env_key() -> None:
    """Test getting env.* config value."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        # Pass local config directly instead of creating files
        local_config = LoadedConfig(
            env={"MY_VAR": "my_value"},
            post_create_commands=[],
            post_create_shell=None,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            local_config=local_config,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "env.MY_VAR"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "my_value" in result.output.strip()


def test_config_get_post_create_shell() -> None:
    """Test getting post_create.shell config value."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        # Pass local config directly instead of creating files
        local_config = LoadedConfig(
            env={},
            post_create_commands=[],
            post_create_shell="/bin/zsh",
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            local_config=local_config,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "post_create.shell"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "/bin/zsh" in result.output.strip()


def test_config_get_post_create_commands() -> None:
    """Test getting post_create.commands config value."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        # Pass local config directly instead of creating files
        local_config = LoadedConfig(
            env={},
            post_create_commands=["echo hello", "echo world"],
            post_create_shell=None,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            local_config=local_config,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "post_create.commands"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "echo hello" in result.output
        assert "echo world" in result.output


def test_config_get_env_key_not_found() -> None:
    """Test that getting non-existent env key fails."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        # Pass empty local config
        local_config = LoadedConfig(
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            local_config=local_config,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "env.NONEXISTENT"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Key not found" in result.output


def test_config_get_invalid_key_format() -> None:
    """Test that invalid key format fails."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        repo_dir = env.erk_root / "repos" / env.cwd.name
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "env"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Invalid key" in result.output


def test_config_get_invalid_key() -> None:
    """Test that getting invalid key fails."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "invalid_key"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Invalid key" in result.output


def test_config_key_with_multiple_dots() -> None:
    """Test that keys with multiple dots are handled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "env.FOO.BAR"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Invalid key" in result.output


def test_config_list_json_with_both_configs() -> None:
    """Test config list --json with both global and repository config."""
    import json

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir}, default_branches={env.cwd: "main"}
        )
        local_config = LoadedConfig(
            env={"FOO": "bar"},
            post_create_commands=["npm install"],
            post_create_shell="/bin/bash",
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            local_config=local_config,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "list", "--json"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)

        # Verify global_config structure
        assert "global_config" in data
        assert data["global_config"] is not None
        assert "erk_root" in data["global_config"]
        assert "use_graphite" in data["global_config"]
        assert "show_pr_info" in data["global_config"]
        assert "exists" in data["global_config"]
        assert data["global_config"]["exists"] is True

        # Verify repository_config structure
        assert "repository_config" in data
        assert data["repository_config"] is not None
        assert data["repository_config"]["trunk_branch"] == "main"
        assert data["repository_config"]["env"] == {"FOO": "bar"}
        assert data["repository_config"]["post_create_shell"] == "/bin/bash"
        assert data["repository_config"]["post_create_commands"] == ["npm install"]


def test_config_list_json_global_only() -> None:
    """Test config list --json with only global config (not in repository)."""
    import json

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # No git directory - FakeGitOps with no repos
        git_ops = FakeGitOps()

        # Build context without repository
        global_config = GlobalConfig(
            erk_root=Path("/fake/erks"),
            use_graphite=False,
            show_pr_info=True,
            shell_setup_complete=False,
        )

        test_ctx = ErkContext.for_test(
            git_ops=git_ops,
            graphite_ops=FakeGraphiteOps(),
            github_ops=FakeGitHubOps(),
            global_config=global_config,
            script_writer=env.script_writer,
            cwd=env.cwd,
            repo=None,
        )

        result = runner.invoke(cli, ["config", "list", "--json"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)

        # Verify global_config is present
        assert "global_config" in data
        assert data["global_config"] is not None
        assert data["global_config"]["exists"] is True

        # Verify repository_config is None
        assert "repository_config" in data
        assert data["repository_config"] is None


def test_config_list_json_with_env_vars() -> None:
    """Test config list --json with environment variables."""
    import json

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir}, default_branches={env.cwd: "main"}
        )
        local_config = LoadedConfig(
            env={"FOO": "bar", "BAZ": "qux"},
            post_create_commands=[],
            post_create_shell=None,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            local_config=local_config,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "list", "--json"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)

        # Verify env dict
        assert data["repository_config"]["env"] == {"FOO": "bar", "BAZ": "qux"}
        assert isinstance(data["repository_config"]["env"], dict)
        # Verify all keys and values are strings
        for key, value in data["repository_config"]["env"].items():
            assert isinstance(key, str)
            assert isinstance(value, str)


def test_config_list_json_with_post_create() -> None:
    """Test config list --json with post-create settings."""
    import json

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir}, default_branches={env.cwd: "main"}
        )
        local_config = LoadedConfig(
            env={},
            post_create_commands=["npm install", "npm build"],
            post_create_shell="bash",
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            local_config=local_config,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "list", "--json"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)

        # Verify post_create_commands is a list of strings
        assert data["repository_config"]["post_create_commands"] == [
            "npm install",
            "npm build",
        ]
        assert isinstance(data["repository_config"]["post_create_commands"], list)

        # Verify post_create_shell
        assert data["repository_config"]["post_create_shell"] == "bash"


def test_config_list_json_validates_schema() -> None:
    """Test config list --json validates against expected schema."""
    import json

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.erk_root / "repos" / env.cwd.name

        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir}, default_branches={env.cwd: "main"}
        )
        local_config = LoadedConfig(
            env={"KEY": "value"},
            post_create_commands=["echo test"],
            post_create_shell="/bin/zsh",
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            use_graphite=True,
            git_ops=git_ops,
            local_config=local_config,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "list", "--json"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)

        # Verify top-level keys
        assert set(data.keys()) == {"global_config", "repository_config"}

        # Verify global_config keys if not None
        if data["global_config"] is not None:
            assert set(data["global_config"].keys()) == {
                "erk_root",
                "use_graphite",
                "show_pr_info",
                "exists",
            }
            assert isinstance(data["global_config"]["erk_root"], str)
            assert isinstance(data["global_config"]["use_graphite"], bool)
            assert isinstance(data["global_config"]["show_pr_info"], bool)
            assert isinstance(data["global_config"]["exists"], bool)

        # Verify repository_config keys if not None
        if data["repository_config"] is not None:
            assert set(data["repository_config"].keys()) == {
                "trunk_branch",
                "env",
                "post_create_shell",
                "post_create_commands",
            }
            # trunk_branch can be str or null
            assert data["repository_config"]["trunk_branch"] is None or isinstance(
                data["repository_config"]["trunk_branch"], str
            )
            # env is always dict
            assert isinstance(data["repository_config"]["env"], dict)
            # post_create_shell can be str or null
            assert data["repository_config"]["post_create_shell"] is None or isinstance(
                data["repository_config"]["post_create_shell"], str
            )
            # post_create_commands is always list
            assert isinstance(data["repository_config"]["post_create_commands"], list)
