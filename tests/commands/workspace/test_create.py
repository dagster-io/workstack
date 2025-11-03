"""Tests for the create command."""

import json
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.global_config_ops import FakeGlobalConfigOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.gitops import WorktreeInfo


def test_create_basic_worktree() -> None:
    """Test creating a basic worktree."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        # Create minimal config
        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        wt_path = workstacks_dir / "test-feature"
        assert wt_path.exists()
        assert (wt_path / ".env").exists()


def test_create_with_custom_branch_name() -> None:
    """Test creating a worktree with a custom branch name."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(
            cli, ["create", "feature", "--branch", "my-custom-branch"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        assert "my-custom-branch" in result.output


def test_create_with_plan_file() -> None:
    """Test creating a worktree with a plan file."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        # Create plan file
        plan_file = cwd / "my-feature-plan.md"
        plan_file.write_text("# My Feature Plan\n", encoding="utf-8")

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["create", "--plan", str(plan_file)], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should create worktree with "plan" stripped from filename
        wt_path = workstacks_dir / "my-feature"
        assert wt_path.exists()
        # Plan file should be moved to .PLAN.md
        assert (wt_path / ".PLAN.md").exists()
        assert not plan_file.exists()


def test_create_with_plan_file_removes_plan_word() -> None:
    """Test that --plan flag removes 'plan' from worktree names."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        # Test multiple plan file examples
        test_cases = [
            ("devclikit-extraction-plan.md", "devclikit-extraction"),
            ("auth-plan.md", "auth"),
            ("plan-for-api.md", "for-api"),
            ("plan.md", "plan"),  # Edge case: only "plan" should be preserved
        ]

        for plan_filename, expected_worktree_name in test_cases:
            # Create plan file
            plan_file = cwd / plan_filename
            plan_file.write_text(f"# {plan_filename}\n", encoding="utf-8")

            result = runner.invoke(cli, ["create", "--plan", str(plan_file)], obj=test_ctx)

            assert result.exit_code == 0, f"Failed for {plan_filename}: {result.output}"
            wt_path = workstacks_dir / expected_worktree_name
            assert wt_path.exists(), f"Expected worktree at {wt_path} for {plan_filename}"
            assert (wt_path / ".PLAN.md").exists()
            assert not plan_file.exists()

            # Clean up for next test
            import shutil

            shutil.rmtree(wt_path)


def test_create_sanitizes_worktree_name() -> None:
    """Test that worktree names are sanitized."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["create", "Test_Feature!!"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # The test verifies the command succeeds - the actual sanitization
        # is tested in test_naming.py. Here we just verify the worktree was created.
        assert workstacks_dir.exists()
        # Check that some worktree directory was created
        created_dirs = [d for d in workstacks_dir.iterdir() if d.is_dir()]
        assert len(created_dirs) > 0, f"No worktree directories created in {workstacks_dir}"


def test_create_sanitizes_branch_name() -> None:
    """Test that branch names are sanitized."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        # Branch name should be sanitized differently than worktree name
        result = runner.invoke(cli, ["create", "Test_Feature!!"], obj=test_ctx)

        assert result.exit_code == 0, result.output


def test_create_detects_default_branch() -> None:
    """Test that create detects the default branch when needed."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
            current_branches={cwd: "feature"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(
            cli, ["create", "new-feature", "--from-current-branch"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output


def test_create_from_current_branch_in_worktree() -> None:
    """Regression: ensure --from-current-branch works when executed from a worktree."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        base = Path.cwd()
        repo_root = base / "repo"
        repo_root.mkdir()
        git_dir = repo_root / ".git"
        git_dir.mkdir()

        current_worktree = base / "wt-current"
        current_worktree.mkdir()

        workstacks_root = base / "workstacks"
        workstacks_root.mkdir()
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir()

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=current_worktree, branch="feature"),
                ]
            },
            current_branches={current_worktree: "feature"},
            default_branches={repo_root: "main"},
            git_common_dirs={
                current_worktree: git_dir,
                repo_root: git_dir,
            },
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        with mock.patch("pathlib.Path.cwd", return_value=current_worktree):
            result = runner.invoke(cli, ["create", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output

        expected_worktree = workstacks_dir / "feature"
        assert expected_worktree.exists()
        assert (expected_worktree / ".env").exists()
        assert (current_worktree, "main") in git_ops.checked_out_branches
        assert (repo_root, "main") not in git_ops.checked_out_branches
        assert (expected_worktree, "feature") in git_ops.added_worktrees


def test_create_fails_if_worktree_exists() -> None:
    """Test that create fails if worktree already exists."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Create existing worktree directory
        wt_path = workstacks_dir / "test-feature"
        wt_path.mkdir(parents=True)

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 1
        assert "already exists" in result.output


def test_create_runs_post_create_commands() -> None:
    """Test that create runs post-create commands."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        # Create config with post_create commands
        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text(
            '[post_create]\ncommands = ["echo hello > test.txt"]\n',
            encoding="utf-8",
        )

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Running post-create commands" in result.output


def test_create_sets_env_variables() -> None:
    """Test that create sets environment variables in .env file."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        # Create config with env vars
        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text(
            '[env]\nMY_VAR = "my_value"\n',
            encoding="utf-8",
        )

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        wt_path = workstacks_dir / "test-feature"
        env_file = wt_path / ".env"
        assert env_file.exists()
        env_content = env_file.read_text(encoding="utf-8")
        assert "MY_VAR" in env_content
        assert "WORKTREE_PATH" in env_content
        assert "REPO_ROOT" in env_content


def test_create_uses_graphite_when_enabled() -> None:
    """Test that create uses graphite when enabled."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
            current_branches={cwd: "main"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=True,
        )
        graphite_ops = FakeGraphiteOps()

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=graphite_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        # Mock subprocess to simulate gt create
        with mock.patch("workstack.cli.commands.create.subprocess.run") as mock_run:
            # Configure mock to return a successful result
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = ""
            result = runner.invoke(cli, ["create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Verify gt create was called
        assert any("gt" in str(call) for call in mock_run.call_args_list)


def test_create_blocks_when_staged_changes_present_with_graphite_enabled() -> None:
    """Ensure the command fails fast when staged changes exist and graphite is enabled."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)
        (workstacks_dir / "config.toml").write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
            current_branches={cwd: "main"},
            staged_repos={cwd},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        with mock.patch("workstack.cli.commands.create.subprocess.run") as mock_run:
            result = runner.invoke(cli, ["create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Staged changes detected." in result.output
        assert 'git commit -m "message"' in result.output
        mock_run.assert_not_called()


def test_create_uses_git_when_graphite_disabled() -> None:
    """Test that create uses git when graphite is disabled."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, result.output


def test_create_allows_staged_changes_when_graphite_disabled() -> None:
    """Graphite disabled path should ignore staged changes and continue."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)
        (workstacks_dir / "config.toml").write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
            staged_repos={cwd},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, result.output


def test_create_invalid_worktree_name() -> None:
    """Test that create rejects invalid worktree names."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={cwd: git_dir})
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        # Test reserved name "root"
        result = runner.invoke(cli, ["create", "root"], obj=test_ctx)
        assert result.exit_code == 1
        assert "reserved" in result.output.lower()

        # Test reserved name "main"
        result = runner.invoke(cli, ["create", "main"], obj=test_ctx)
        assert result.exit_code == 1
        assert "cannot be used" in result.output.lower()

        # Test reserved name "master"
        result = runner.invoke(cli, ["create", "master"], obj=test_ctx)
        assert result.exit_code == 1
        assert "cannot be used" in result.output.lower()


def test_create_plan_file_not_found() -> None:
    """Test that create fails when plan file doesn't exist."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={cwd: git_dir})
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["create", "--plan", "nonexistent.md"], obj=test_ctx)

        # Click should fail validation before reaching our code
        assert result.exit_code != 0


def test_create_no_post_flag_skips_commands() -> None:
    """Test that --no-post flag skips post-create commands."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        # Create config with post_create commands
        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text(
            '[post_create]\ncommands = ["echo hello"]\n',
            encoding="utf-8",
        )

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["create", "test-feature", "--no-post"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Running post-create commands" not in result.output


def test_create_from_current_branch() -> None:
    """Test creating worktree from current branch."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
            current_branches={cwd: "feature-branch"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["create", "feature", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output


def test_create_from_branch() -> None:
    """Test creating worktree from an existing branch."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(
            cli, ["create", "feature", "--from-branch", "existing-branch"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output


def test_create_requires_name_or_flag() -> None:
    """Test that create requires NAME or a flag."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={cwd: git_dir})
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["create"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Must provide NAME" in result.output


def test_create_from_current_branch_on_main_fails() -> None:
    """Test that --from-current-branch fails with helpful message when on main."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
            current_branches={cwd: "main"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["create", "feature", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Cannot use --from-current-branch when on 'main'" in result.output
        assert "Alternatives:" in result.output


def test_create_detects_branch_already_checked_out() -> None:
    """Test that create detects when branch is already checked out."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Setup: feature-branch is already checked out in an existing worktree
        existing_wt_path = workstacks_dir / "existing-feature"
        existing_wt_path.mkdir(parents=True)

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
            current_branches={cwd: "main"},
            worktrees={
                cwd: [
                    WorktreeInfo(path=cwd, branch="main"),
                    WorktreeInfo(path=existing_wt_path, branch="feature-branch"),
                ],
            },
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(
            cli, ["create", "new-feature", "--from-branch", "feature-branch"], obj=test_ctx
        )

        assert result.exit_code == 1
        assert "already checked out" in result.output
        assert "feature-branch" in result.output


def test_create_from_current_branch_on_master_fails() -> None:
    """Test that --from-current-branch fails when on master branch too."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "master"},
            current_branches={cwd: "master"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["create", "feature", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Cannot use --from-current-branch when on 'master'" in result.output


def test_create_with_keep_plan_flag() -> None:
    """Test that --keep-plan copies instead of moves the plan file."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        # Create plan file
        plan_file = cwd / "my-feature-plan.md"
        plan_file.write_text("# My Feature Plan\n", encoding="utf-8")

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(
            cli, ["create", "--plan", str(plan_file), "--keep-plan"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        # Should create worktree with "plan" stripped from filename
        wt_path = workstacks_dir / "my-feature"
        assert wt_path.exists()
        # Plan file should be copied to .PLAN.md
        assert (wt_path / ".PLAN.md").exists()
        # Original plan file should still exist (copied, not moved)
        assert plan_file.exists()
        assert "Copied plan to" in result.output


def test_create_keep_plan_without_plan_fails() -> None:
    """Test that --keep-plan without --plan fails with error message."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"

        git_ops = FakeGitOps(git_common_dirs={cwd: git_dir})
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["create", "test-feature", "--keep-plan"], obj=test_ctx)

        assert result.exit_code == 1
        assert "--keep-plan requires --plan" in result.output


def test_from_current_branch_with_main_in_use_prefers_graphite_parent() -> None:
    """Test that --from-current-branch prefers Graphite parent when main is in use.

    Scenario:
    - Current worktree is on feature-2 (with Graphite parent feature-1)
    - Root worktree has main checked out
    - feature-1 is available (not checked out)

    Expected: Should checkout feature-1 (the parent), not try to checkout main
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        base = Path.cwd()
        repo_root = base / "repo"
        repo_root.mkdir()
        git_dir = repo_root / ".git"
        git_dir.mkdir()

        current_worktree = base / "wt-current"
        current_worktree.mkdir()

        workstacks_root = base / "workstacks"
        workstacks_root.mkdir()
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir()

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Set up Graphite stack: main -> feature-1 -> feature-2
        from tests.test_utils.graphite_helpers import setup_graphite_stack

        setup_graphite_stack(
            git_dir,
            {
                "main": {"parent": None, "children": ["feature-1"], "is_trunk": True},
                "feature-1": {"parent": "main", "children": ["feature-2"]},
                "feature-2": {"parent": "feature-1", "children": []},
            },
        )

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=current_worktree, branch="feature-2"),
                ]
            },
            current_branches={
                repo_root: "main",
                current_worktree: "feature-2",
            },
            default_branches={repo_root: "main"},
            git_common_dirs={
                current_worktree: git_dir,
                repo_root: git_dir,
            },
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        with mock.patch("pathlib.Path.cwd", return_value=current_worktree):
            result = runner.invoke(cli, ["create", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should checkout feature-1 (the Graphite parent), not main
        assert (current_worktree, "feature-1") in git_ops.checked_out_branches


def test_from_current_branch_with_parent_in_use_falls_back_to_detached_head() -> None:
    """Test that --from-current-branch uses detached HEAD when parent is also in use.

    Scenario:
    - Current worktree is on feature-2 (with Graphite parent feature-1)
    - Root worktree has main checked out
    - Another worktree has feature-1 checked out

    Expected: Should use detached HEAD as fallback since both main and parent are in use
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        base = Path.cwd()
        repo_root = base / "repo"
        repo_root.mkdir()
        git_dir = repo_root / ".git"
        git_dir.mkdir()

        current_worktree = base / "wt-current"
        current_worktree.mkdir()

        other_worktree = base / "wt-other"
        other_worktree.mkdir()

        workstacks_root = base / "workstacks"
        workstacks_root.mkdir()
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir()

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Set up Graphite stack: main -> feature-1 -> feature-2
        from tests.test_utils.graphite_helpers import setup_graphite_stack

        setup_graphite_stack(
            git_dir,
            {
                "main": {"parent": None, "children": ["feature-1"], "is_trunk": True},
                "feature-1": {"parent": "main", "children": ["feature-2"]},
                "feature-2": {"parent": "feature-1", "children": []},
            },
        )

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=current_worktree, branch="feature-2"),
                    WorktreeInfo(path=other_worktree, branch="feature-1"),
                ]
            },
            current_branches={
                repo_root: "main",
                current_worktree: "feature-2",
                other_worktree: "feature-1",
            },
            default_branches={repo_root: "main"},
            git_common_dirs={
                current_worktree: git_dir,
                repo_root: git_dir,
                other_worktree: git_dir,
            },
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        with mock.patch("pathlib.Path.cwd", return_value=current_worktree):
            result = runner.invoke(cli, ["create", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should use detached HEAD since both main and feature-1 are in use
        assert len(git_ops.detached_checkouts) == 1
        assert git_ops.detached_checkouts[0][0] == current_worktree
        assert git_ops.detached_checkouts[0][1] == "feature-2"


def test_from_current_branch_without_graphite_falls_back_to_main() -> None:
    """Test that --from-current-branch falls back to main when no Graphite parent exists.

    Scenario:
    - Current worktree is on standalone-feature (not in any Graphite stack)
    - Root worktree has other-branch checked out (not main)
    - main is available

    Expected: Should checkout main as fallback
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        base = Path.cwd()
        repo_root = base / "repo"
        repo_root.mkdir()
        git_dir = repo_root / ".git"
        git_dir.mkdir()

        current_worktree = base / "wt-current"
        current_worktree.mkdir()

        workstacks_root = base / "workstacks"
        workstacks_root.mkdir()
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir()

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Set up minimal Graphite stack (standalone-feature not in it)
        from tests.test_utils.graphite_helpers import setup_graphite_stack

        setup_graphite_stack(
            git_dir,
            {
                "main": {"parent": None, "children": [], "is_trunk": True},
            },
        )

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="other-branch"),
                    WorktreeInfo(path=current_worktree, branch="standalone-feature"),
                ]
            },
            current_branches={
                repo_root: "other-branch",
                current_worktree: "standalone-feature",
            },
            default_branches={repo_root: "main"},
            git_common_dirs={
                current_worktree: git_dir,
                repo_root: git_dir,
            },
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        with mock.patch("pathlib.Path.cwd", return_value=current_worktree):
            result = runner.invoke(cli, ["create", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should checkout main since no Graphite parent exists
        assert (current_worktree, "main") in git_ops.checked_out_branches


def test_from_current_branch_no_graphite_main_in_use_uses_detached_head() -> None:
    """Test that --from-current-branch uses detached HEAD when no parent and main is in use.

    Scenario:
    - Current worktree is on standalone-feature (not in any Graphite stack)
    - Root worktree has main checked out

    Expected: Should use detached HEAD since no parent exists and main is in use
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        base = Path.cwd()
        repo_root = base / "repo"
        repo_root.mkdir()
        git_dir = repo_root / ".git"
        git_dir.mkdir()

        current_worktree = base / "wt-current"
        current_worktree.mkdir()

        workstacks_root = base / "workstacks"
        workstacks_root.mkdir()
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir()

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Set up minimal Graphite stack (standalone-feature not in it)
        from tests.test_utils.graphite_helpers import setup_graphite_stack

        setup_graphite_stack(
            git_dir,
            {
                "main": {"parent": None, "children": [], "is_trunk": True},
            },
        )

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=current_worktree, branch="standalone-feature"),
                ]
            },
            current_branches={
                repo_root: "main",
                current_worktree: "standalone-feature",
            },
            default_branches={repo_root: "main"},
            git_common_dirs={
                current_worktree: git_dir,
                repo_root: git_dir,
            },
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        with mock.patch("pathlib.Path.cwd", return_value=current_worktree):
            result = runner.invoke(cli, ["create", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should use detached HEAD since no parent and main is in use
        assert len(git_ops.detached_checkouts) == 1
        assert git_ops.detached_checkouts[0][0] == current_worktree
        assert git_ops.detached_checkouts[0][1] == "standalone-feature"


def test_create_with_json_output() -> None:
    """Test creating a worktree with JSON output."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["create", "test-feature", "--json"], obj=test_ctx)

        assert result.exit_code == 0, result.output

        # Verify JSON output
        output_data = json.loads(result.output)
        assert output_data["worktree_name"] == "test-feature"
        assert output_data["worktree_path"] == str(workstacks_dir / "test-feature")
        assert output_data["branch_name"] == "test-feature"
        assert output_data["plan_file"] is None
        assert output_data["status"] == "created"

        # Verify worktree was actually created
        wt_path = workstacks_dir / "test-feature"
        assert wt_path.exists()


def test_create_existing_worktree_with_json() -> None:
    """Test creating a worktree that already exists with JSON output."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Create existing worktree
        existing_wt = workstacks_dir / "existing-feature"
        existing_wt.mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
            current_branches={existing_wt: "existing-branch"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["create", "existing-feature", "--json"], obj=test_ctx)

        assert result.exit_code == 1, result.output

        # Verify JSON error output
        output_data = json.loads(result.output)
        assert output_data["worktree_name"] == "existing-feature"
        assert output_data["worktree_path"] == str(existing_wt)
        assert output_data["branch_name"] == "existing-branch"
        assert output_data["status"] == "exists"


def test_create_json_and_script_mutually_exclusive() -> None:
    """Test that --json and --script flags are mutually exclusive."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(
            cli, ["create", "test-feature", "--json", "--script"], obj=test_ctx
        )

        # Should fail with validation error
        assert result.exit_code == 1
        assert "Cannot use both --json and --script" in result.output


def test_create_with_json_and_plan_file() -> None:
    """Test creating a worktree with JSON output and plan file."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Create a plan file - name will be derived from filename
        plan_file = cwd / "test-feature-plan.md"
        plan_file.write_text("# Implementation Plan\n\nTest plan content", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        # Don't provide NAME - it's derived from plan filename
        result = runner.invoke(
            cli,
            ["create", "--json", "--plan", str(plan_file)],
            obj=test_ctx,
        )

        assert result.exit_code == 0, result.output

        # Verify JSON output includes plan file
        output_data = json.loads(result.output)
        # Name is derived from "test-feature-plan.md" -> "test-feature"
        assert output_data["worktree_name"] == "test-feature"
        wt_path = workstacks_dir / "test-feature"
        expected_plan_path = wt_path / ".PLAN.md"
        assert output_data["plan_file"] == str(expected_plan_path)
        assert output_data["status"] == "created"

        # Verify plan file was moved
        assert expected_plan_path.exists()
        assert not plan_file.exists()  # Original should be moved, not copied


def test_create_with_json_no_plan() -> None:
    """Test that JSON output has null plan_file when no plan is provided."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = cwd / ".git"
        git_dir.mkdir()

        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / cwd.name
        workstacks_dir.mkdir(parents=True)

        config_toml = workstacks_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGitOps(
            git_common_dirs={cwd: git_dir},
            default_branches={cwd: "main"},
        )
        global_config_ops = FakeGlobalConfigOps(
            exists=True,
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["create", "test-feature", "--json"], obj=test_ctx)

        assert result.exit_code == 0, result.output

        # Verify JSON output has null plan_file
        output_data = json.loads(result.output)
        assert output_data["plan_file"] is None
        assert output_data["status"] == "created"
