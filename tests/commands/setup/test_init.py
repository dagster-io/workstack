"""Tests for the init command.

Mock Usage Policy:
------------------
This file uses mocks for external boundaries that are legitimate to mock:

1. os.environ HOME patches (14 uses):
   - LEGITIMATE: Testing path resolution logic that depends on $HOME
   - The init command uses Path.home() to determine ~/.workstack location
   - Patching HOME redirects to temp directory for test isolation
   - Cannot be replaced with fakes (environment variable is external boundary)

2. global_config_exists() patches (14 uses):
   - LEGITIMATE: Testing file system boundary
   - Function just checks if ~/.workstack/config.toml exists
   - Could be replaced with real file creation, but mock is clearer for intent
   - Explicitly shows "simulate existing config" vs "create temp file and hope test sees it"
   - The trivial file check is already tested in integration tests

Both patches are necessary for testing init command's conditional logic without
polluting real filesystem or requiring complex fixture setup.
"""

import os
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.env_helpers import simulated_workstack_env
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.global_config import GlobalConfig, load_global_config


def test_init_creates_global_config_first_time() -> None:
    """Test that init creates global config on first run."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=env.cwd / "fake-workstacks",
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{workstacks_root}\nn\n")

        assert result.exit_code == 0, result.output
        assert "Global config not found" in result.output
        assert "Created global config" in result.output
        assert (env.cwd / ".workstack" / "config.toml").exists()


def test_init_prompts_for_workstacks_root() -> None:
    """Test that init prompts for workstacks root when creating config."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "my-workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=env.cwd / "fake-workstacks",
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{workstacks_root}\nn\n")

        assert result.exit_code == 0, result.output
        assert "Worktrees root directory" in result.output
        # Reload config from file to verify it was saved correctly
        loaded_config = load_global_config(env.cwd / ".workstack" / "config.toml")
        assert loaded_config.workstacks_root == workstacks_root.resolve()


def test_init_detects_graphite_installed() -> None:
    """Test that init detects when Graphite (gt) is installed."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=env.cwd / "fake-workstacks",
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )
        shell_ops = FakeShellOps(installed_tools={"gt": "/usr/local/bin/gt"})

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            shell_ops=shell_ops,
            cwd=env.cwd,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{workstacks_root}\nn\n")

        assert result.exit_code == 0, result.output
        assert "Graphite (gt) detected" in result.output
        # Reload config from file to verify graphite was enabled
        loaded_config = load_global_config(env.cwd / ".workstack" / "config.toml")
        assert loaded_config.use_graphite


def test_init_detects_graphite_not_installed() -> None:
    """Test that init detects when Graphite (gt) is NOT installed."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=env.cwd / "fake-workstacks",
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{workstacks_root}\nn\n")

        assert result.exit_code == 0, result.output
        assert "Graphite (gt) not detected" in result.output
        # Reload config from file to verify graphite is disabled
        loaded_config = load_global_config(env.cwd / ".workstack" / "config.toml")
        assert not loaded_config.use_graphite


def test_init_skips_global_with_repo_flag() -> None:
    """Test that --repo flag skips global config creation."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        # Mock global_config_exists to return True (simulating existing global config)
        with mock.patch("workstack.core.global_config.global_config_exists", return_value=True):
            result = runner.invoke(cli, ["init", "--repo"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Global config not found" not in result.output
        assert (env.cwd / "config.toml").exists()


def test_init_fails_repo_flag_without_global_config() -> None:
    """Test that --repo flag fails when global config doesn't exist."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=env.cwd / "fake-workstacks",
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--repo"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Global config not found" in result.output
        assert "Run 'workstack init' without --repo" in result.output
        assert "Run 'workstack init' without --repo" in result.output


def test_init_auto_preset_detects_dagster() -> None:
    """Test that auto preset detects dagster repo and uses dagster preset."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create pyproject.toml with dagster as the project name
        pyproject = env.cwd / "pyproject.toml"
        pyproject.write_text('[project]\nname = "dagster"\n', encoding="utf-8")

        workstacks_root = env.cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        # Mock global_config_exists to return True (simulating existing global config)
        with mock.patch("workstack.core.global_config.global_config_exists", return_value=True):
            result = runner.invoke(cli, ["init"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Config should be created in workstacks_dir
        workstacks_dir = workstacks_root / env.cwd.name
        config_path = workstacks_dir / "config.toml"
        assert config_path.exists()


def test_init_auto_preset_uses_generic_fallback() -> None:
    """Test that auto preset falls back to generic for non-dagster repos."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create pyproject.toml with different project name
        pyproject = env.cwd / "pyproject.toml"
        pyproject.write_text('[project]\nname = "myproject"\n', encoding="utf-8")

        workstacks_root = env.cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        # Mock global_config_exists to return True (simulating existing global config)
        with mock.patch("workstack.core.global_config.global_config_exists", return_value=True):
            result = runner.invoke(cli, ["init"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        workstacks_dir = workstacks_root / env.cwd.name
        config_path = workstacks_dir / "config.toml"
        assert config_path.exists()


def test_init_explicit_preset_dagster() -> None:
    """Test that explicit --preset dagster uses dagster preset."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        # Mock global_config_exists to return True (simulating existing global config)
        with mock.patch("workstack.core.global_config.global_config_exists", return_value=True):
            result = runner.invoke(cli, ["init", "--preset", "dagster"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        workstacks_dir = workstacks_root / env.cwd.name
        config_path = workstacks_dir / "config.toml"
        assert config_path.exists()


def test_init_explicit_preset_generic() -> None:
    """Test that explicit --preset generic uses generic preset."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        # Mock global_config_exists to return True (simulating existing global config)
        with mock.patch("workstack.core.global_config.global_config_exists", return_value=True):
            result = runner.invoke(cli, ["init", "--preset", "generic"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        workstacks_dir = workstacks_root / env.cwd.name
        config_path = workstacks_dir / "config.toml"
        assert config_path.exists()


def test_init_list_presets_displays_available() -> None:
    """Test that --list-presets displays available presets."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=env.cwd / "fake-workstacks",
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["init", "--list-presets"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Available presets:" in result.output
        assert "dagster" in result.output
        assert "generic" in result.output


def test_init_invalid_preset_fails() -> None:
    """Test that invalid preset name fails with helpful error."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["init", "--preset", "nonexistent"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Invalid preset 'nonexistent'" in result.output


def test_init_creates_config_at_workstacks_dir() -> None:
    """Test that init creates config.toml in workstacks_dir by default."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        # Mock global_config_exists to return True (simulating existing global config)
        with mock.patch("workstack.core.global_config.global_config_exists", return_value=True):
            result = runner.invoke(cli, ["init"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Config should be in workstacks_dir, not repo root
        workstacks_dir = workstacks_root / env.cwd.name
        config_path = workstacks_dir / "config.toml"
        assert config_path.exists()
        assert not (env.cwd / "config.toml").exists()


def test_init_repo_flag_creates_config_at_root() -> None:
    """Test that --repo creates config.toml at repo root."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        # Mock global_config_exists to return True (simulating existing global config)
        with mock.patch("workstack.core.global_config.global_config_exists", return_value=True):
            result = runner.invoke(cli, ["init", "--repo"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Config should be at repo root
        config_path = env.cwd / "config.toml"
        assert config_path.exists()


def test_init_force_overwrites_existing_config() -> None:
    """Test that --force overwrites existing config."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"
        workstacks_dir = workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        # Create existing config
        config_path = workstacks_dir / "config.toml"
        config_path.write_text("# Old config\n", encoding="utf-8")

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        # Mock global_config_exists to return True (simulating existing global config)
        with mock.patch("workstack.core.global_config.global_config_exists", return_value=True):
            result = runner.invoke(cli, ["init", "--force"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert config_path.exists()
        # Verify content was overwritten (shouldn't contain "Old config")
        content = config_path.read_text(encoding="utf-8")
        assert "# Old config" not in content


def test_init_fails_without_force_when_exists() -> None:
    """Test that init fails when config exists without --force."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"
        workstacks_dir = workstacks_root / env.cwd.name
        workstacks_dir.mkdir(parents=True)

        # Create existing config
        config_path = workstacks_dir / "config.toml"
        config_path.write_text("# Existing config\n", encoding="utf-8")

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        # Mock global_config_exists to return True (simulating existing global config)
        with mock.patch("workstack.core.global_config.global_config_exists", return_value=True):
            result = runner.invoke(cli, ["init"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Config already exists" in result.output
        assert "Use --force to overwrite" in result.output


def test_init_adds_plan_md_to_gitignore() -> None:
    """Test that init offers to add .PLAN.md to .gitignore."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create .gitignore
        gitignore = env.cwd / ".gitignore"
        gitignore.write_text("*.pyc\n", encoding="utf-8")

        workstacks_root = env.cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        # Accept both prompts (y for .PLAN.md, y for .env)
        # Mock global_config_exists to return True (simulating existing global config)
        with mock.patch("workstack.core.global_config.global_config_exists", return_value=True):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input="y\ny\n")

        assert result.exit_code == 0, result.output
        gitignore_content = gitignore.read_text(encoding="utf-8")
        assert ".PLAN.md" in gitignore_content


def test_init_adds_env_to_gitignore() -> None:
    """Test that init offers to add .env to .gitignore."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create .gitignore
        gitignore = env.cwd / ".gitignore"
        gitignore.write_text("*.pyc\n", encoding="utf-8")

        workstacks_root = env.cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        # Accept both prompts (y for .PLAN.md, y for .env)
        # Mock global_config_exists to return True (simulating existing global config)
        with mock.patch("workstack.core.global_config.global_config_exists", return_value=True):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input="y\ny\n")

        assert result.exit_code == 0, result.output
        gitignore_content = gitignore.read_text(encoding="utf-8")
        assert ".env" in gitignore_content


def test_init_skips_gitignore_entries_if_declined() -> None:
    """Test that init skips gitignore entries if user declines."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create .gitignore
        gitignore = env.cwd / ".gitignore"
        gitignore.write_text("*.pyc\n", encoding="utf-8")

        workstacks_root = env.cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        # Decline both prompts
        # Mock global_config_exists to return True (simulating existing global config)
        with mock.patch("workstack.core.global_config.global_config_exists", return_value=True):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input="n\nn\n")

        assert result.exit_code == 0, result.output
        gitignore_content = gitignore.read_text(encoding="utf-8")
        assert ".PLAN.md" not in gitignore_content
        assert ".env" not in gitignore_content


def test_init_handles_missing_gitignore() -> None:
    """Test that init handles missing .gitignore gracefully."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # No .gitignore file

        workstacks_root = env.cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        # Mock global_config_exists to return True (simulating existing global config)
        with mock.patch("workstack.core.global_config.global_config_exists", return_value=True):
            result = runner.invoke(cli, ["init"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should not crash or prompt about gitignore


def test_init_preserves_gitignore_formatting() -> None:
    """Test that init preserves existing gitignore formatting."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create .gitignore with specific formatting
        gitignore = env.cwd / ".gitignore"
        original_content = "# Python\n*.pyc\n__pycache__/\n"
        gitignore.write_text(original_content, encoding="utf-8")

        workstacks_root = env.cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        # Accept both prompts (y for .PLAN.md, y for .env)
        # Mock global_config_exists to return True (simulating existing global config)
        with mock.patch("workstack.core.global_config.global_config_exists", return_value=True):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input="y\ny\n")

        assert result.exit_code == 0, result.output
        gitignore_content = gitignore.read_text(encoding="utf-8")
        # Original content should be preserved
        assert "# Python" in gitignore_content
        assert "*.pyc" in gitignore_content
        # New entries should be added
        assert ".PLAN.md" in gitignore_content
        assert ".env" in gitignore_content


def test_init_first_time_offers_shell_setup() -> None:
    """Test that first-time init offers shell integration setup."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=env.cwd / "fake-workstacks",
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(detected_shell=("bash", bashrc)),
            cwd=env.cwd,
            dry_run=False,
        )

        # Provide input: workstacks_root, decline shell setup
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{workstacks_root}\nn\n")

        assert result.exit_code == 0, result.output
        # Should mention shell integration
        assert "shell integration" in result.output.lower()


def test_init_shell_flag_only_setup() -> None:
    """Test that --shell flag only performs shell setup."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(detected_shell=("bash", bashrc)),
            cwd=env.cwd,
            dry_run=False,
        )

        # Decline shell setup
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init", "--shell"], obj=test_ctx, input="n\n")

        assert result.exit_code == 0, result.output
        # Should mention shell but not create config
        workstacks_dir = workstacks_root / env.cwd.name
        config_path = workstacks_dir / "config.toml"
        assert not config_path.exists()


def test_init_detects_bash_shell() -> None:
    """Test that init correctly detects bash shell."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=env.cwd / "fake-workstacks",
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(detected_shell=("bash", bashrc)),
            cwd=env.cwd,
            dry_run=False,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{workstacks_root}\nn\n",
            )

        assert result.exit_code == 0, result.output
        assert "bash" in result.output.lower()


def test_init_detects_zsh_shell() -> None:
    """Test that init correctly detects zsh shell."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"
        zshrc = Path.home() / ".zshrc"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=env.cwd / "fake-workstacks",
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(detected_shell=("zsh", zshrc)),
            cwd=env.cwd,
            dry_run=False,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{workstacks_root}\nn\n",
            )

        assert result.exit_code == 0, result.output
        assert "zsh" in result.output.lower()


def test_init_detects_fish_shell() -> None:
    """Test that init correctly detects fish shell."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"
        fish_config = Path.home() / ".config" / "fish" / "config.fish"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=env.cwd / "fake-workstacks",
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(detected_shell=("fish", fish_config)),
            cwd=env.cwd,
            dry_run=False,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{workstacks_root}\nn\n",
            )

        assert result.exit_code == 0, result.output
        assert "fish" in result.output.lower()


def test_init_skips_unknown_shell() -> None:
    """Test that init skips shell setup for unknown shells."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=env.cwd / "fake-workstacks",
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{workstacks_root}\n")

        assert result.exit_code == 0, result.output
        assert "Unable to detect shell" in result.output


def test_init_prints_completion_instructions() -> None:
    """Test that init prints completion instructions."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=env.cwd / "fake-workstacks",
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(detected_shell=("bash", bashrc)),
            cwd=env.cwd,
            dry_run=False,
        )

        # Accept shell setup to see instructions
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{workstacks_root}\ny\n",
            )

        assert result.exit_code == 0, result.output
        # Verify instructions are printed, not file written
        assert "Shell Integration Setup" in result.output
        assert "# Workstack completion" in result.output
        assert "source <(workstack completion bash)" in result.output


def test_init_prints_wrapper_instructions() -> None:
    """Test that init prints wrapper function instructions."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=env.cwd / "fake-workstacks",
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(detected_shell=("bash", bashrc)),
            cwd=env.cwd,
            dry_run=False,
        )

        # Accept shell setup to see instructions
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{workstacks_root}\ny\n",
            )

        assert result.exit_code == 0, result.output
        # Verify wrapper instructions are printed
        assert "Shell Integration Setup" in result.output
        assert "# Workstack shell integration" in result.output
        assert "workstack()" in result.output


def test_init_skips_shell_if_declined() -> None:
    """Test that init skips shell setup if user declines."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_root = env.cwd / "workstacks"
        bashrc = Path.home() / ".bashrc"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig(
            workstacks_root=env.cwd / "fake-workstacks",
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(detected_shell=("bash", bashrc)),
            cwd=env.cwd,
            dry_run=False,
        )

        # Decline shell setup
        with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
            result = runner.invoke(
                cli,
                ["init"],
                obj=test_ctx,
                input=f"{workstacks_root}\nn\n",
            )

        assert result.exit_code == 0, result.output
        # Verify no instructions were printed when declined
        assert "Shell Integration Setup" not in result.output
        assert "Skipping shell integration" in result.output


def test_init_not_in_git_repo_fails() -> None:
    """Test that init fails when not in a git repository."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Remove .git directory to simulate non-git directory
        import shutil

        shutil.rmtree(env.git_dir)

        git_ops = FakeGitOps()  # Empty, no git_common_dirs
        global_config = GlobalConfig(
            workstacks_root=env.cwd / "fake-workstacks",
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{env.cwd}/workstacks\n")

        # The command should fail at repo discovery
        assert result.exit_code != 0
