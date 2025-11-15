import os
from datetime import datetime
from pathlib import Path

from click.testing import CliRunner

from tests.fakes.gitops import FakeGitOps
from tests.test_utils.env_helpers import simulated_workstack_env
from workstack.cli.cli import cli
from workstack.cli.commands.shell_integration import hidden_shell_cmd
from workstack.cli.shell_utils import render_cd_script
from workstack.core.context import WorkstackContext
from workstack.core.gitops import WorktreeInfo
from workstack.core.global_config import GlobalConfig, InMemoryGlobalConfigOps


def test_create_with_plan_file() -> None:
    """Test creating a worktree from a plan file."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create a plan file in root worktree
        plan_file = env.root_worktree / "Add_Auth_Feature.md"
        plan_content = "# Auth Feature Plan\n\n- Add login\n- Add signup\n"
        plan_file.write_text(plan_content, encoding="utf-8")

        # Configure FakeGitOps with root worktree only
        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            default_branches={env.root_worktree: "main"},
        )

        # Create test context using env.build_context() helper
        test_ctx = env.build_context(git_ops=git_ops)

        # Run workstack create with --plan
        result = runner.invoke(
            cli, ["create", "--plan", "Add_Auth_Feature.md", "--no-post"], obj=test_ctx
        )
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # --plan flag adds date suffix in format -YY-MM-DD
        date_suffix = datetime.now().strftime("%y-%m-%d")
        expected_name = f"add-auth-feature-{date_suffix}"

        # Verify worktree was created with sanitized name and date suffix
        worktree_path = env.workstacks_root / "repo" / expected_name
        assert worktree_path.exists()
        assert worktree_path.is_dir()

        # Verify plan folder was created with plan.md and progress.md
        plan_folder = worktree_path / ".plan"
        assert plan_folder.exists()
        assert (plan_folder / "plan.md").exists()
        assert (plan_folder / "plan.md").read_text(encoding="utf-8") == plan_content
        assert (plan_folder / "progress.md").exists()

        # Verify original plan file was moved (not copied)
        assert not plan_file.exists()

        # Verify .env was created
        assert (worktree_path / ".env").exists()


def test_create_with_plan_name_sanitization() -> None:
    """Test that plan filename gets properly sanitized for worktree name."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create a plan file with underscores and mixed case
        plan_file = env.root_worktree / "MY_COOL_Plan_File.md"
        plan_file.write_text("# Cool Plan\n", encoding="utf-8")

        # Configure FakeGitOps with root worktree only
        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            default_branches={env.root_worktree: "main"},
        )

        # Create test context using env.build_context() helper
        test_ctx = env.build_context(git_ops=git_ops)

        # Run workstack create with --plan
        result = runner.invoke(
            cli, ["create", "--plan", "MY_COOL_Plan_File.md", "--no-post"], obj=test_ctx
        )
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # --plan flag adds date suffix in format -YY-MM-DD
        date_suffix = datetime.now().strftime("%y-%m-%d")
        expected_name = f"my-cool-file-{date_suffix}"

        # Verify worktree name is lowercase with hyphens, "plan" removed, and date suffix added
        worktree_path = env.workstacks_root / "repo" / expected_name
        assert worktree_path.exists()

        # Verify plan folder was created
        assert (worktree_path / ".plan" / "plan.md").exists()
        assert (worktree_path / ".plan" / "progress.md").exists()
        assert not plan_file.exists()


def test_create_with_both_name_and_plan_fails() -> None:
    """Test that providing both NAME and --plan is an error."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create a plan file
        plan_file = env.root_worktree / "plan.md"
        plan_file.write_text("# Plan\n", encoding="utf-8")

        # Configure FakeGitOps with root worktree only
        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            default_branches={env.root_worktree: "main"},
        )

        # Create global config with workstacks_root
        global_config = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )
        global_config_ops = InMemoryGlobalConfigOps(config=global_config)

        # Create test context
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            global_config=global_config,
            script_writer=env.script_writer,
            cwd=env.root_worktree,
        )

        # Run workstack create with both NAME and --plan
        result = runner.invoke(cli, ["create", "myname", "--plan", "plan.md"], obj=test_ctx)

        # Should fail
        assert result.exit_code != 0
        assert "Cannot specify both NAME and --plan" in result.output


def test_create_rejects_reserved_name_root() -> None:
    """Test that 'root' is rejected as a reserved worktree name."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure FakeGitOps with root worktree only
        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            default_branches={env.root_worktree: "main"},
        )

        # Create global config with workstacks_root
        global_config = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )
        global_config_ops = InMemoryGlobalConfigOps(config=global_config)

        # Create test context
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            global_config=global_config,
            script_writer=env.script_writer,
            cwd=env.root_worktree,
        )

        # Try to create a worktree named "root"
        result = runner.invoke(cli, ["create", "root", "--no-post"], obj=test_ctx)

        # Should fail with reserved name error
        assert result.exit_code != 0
        assert "root" in result.output.lower() and "reserved" in result.output.lower(), (
            f"Expected error about 'root' being reserved, got: {result.output}"
        )

        # Verify worktree was not created
        worktree_path = env.workstacks_root / "repo" / "root"
        assert not worktree_path.exists()


def test_create_rejects_reserved_name_root_case_insensitive() -> None:
    """Test that 'ROOT', 'Root', etc. are also rejected (case-insensitive)."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure FakeGitOps with root worktree only
        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            default_branches={env.root_worktree: "main"},
        )

        # Create global config with workstacks_root
        global_config = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )
        global_config_ops = InMemoryGlobalConfigOps(config=global_config)

        # Create test context
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            global_config=global_config,
            script_writer=env.script_writer,
            cwd=env.root_worktree,
        )

        # Test various cases of "root"
        for name_variant in ["ROOT", "Root", "RoOt"]:
            result = runner.invoke(cli, ["create", name_variant, "--no-post"], obj=test_ctx)

            # Should fail with reserved name error
            assert result.exit_code != 0, f"Expected failure for name '{name_variant}'"
            error_msg = (
                f"Expected error about 'root' being reserved for '{name_variant}', "
                f"got: {result.output}"
            )
            assert "reserved" in result.output.lower(), error_msg


def test_create_rejects_main_as_worktree_name() -> None:
    """Test that 'main' is rejected as a worktree name."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure FakeGitOps with root worktree only
        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            default_branches={env.root_worktree: "main"},
        )

        # Create global config with workstacks_root
        global_config = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )
        global_config_ops = InMemoryGlobalConfigOps(config=global_config)

        # Create test context
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            global_config=global_config,
            script_writer=env.script_writer,
            cwd=env.root_worktree,
        )

        # Try to create a worktree named "main"
        result = runner.invoke(cli, ["create", "main", "--no-post"], obj=test_ctx)

        # Should fail with error suggesting to use root
        assert result.exit_code != 0
        assert "main" in result.output.lower()
        assert "workstack switch root" in result.output

        # Verify worktree was not created
        worktree_path = env.workstacks_root / "repo" / "main"
        assert not worktree_path.exists()


def test_create_rejects_master_as_worktree_name() -> None:
    """Test that 'master' is rejected as a worktree name."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure FakeGitOps with root worktree only
        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            default_branches={env.root_worktree: "main"},
        )

        # Create global config with workstacks_root
        global_config = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )
        global_config_ops = InMemoryGlobalConfigOps(config=global_config)

        # Create test context
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            global_config=global_config,
            script_writer=env.script_writer,
            cwd=env.root_worktree,
        )

        # Try to create a worktree named "master"
        result = runner.invoke(cli, ["create", "master", "--no-post"], obj=test_ctx)

        # Should fail with error suggesting to use root
        assert result.exit_code != 0
        assert "master" in result.output.lower()
        assert "workstack switch root" in result.output

        # Verify worktree was not created
        worktree_path = env.workstacks_root / "repo" / "master"
        assert not worktree_path.exists()


def test_render_cd_script() -> None:
    """Test that render_cd_script generates proper shell code."""
    worktree_path = Path("/example/workstacks/repo/my-worktree")
    script = render_cd_script(
        worktree_path,
        comment="workstack create - cd to new worktree",
        success_message="✓ Switched to new worktree.",
    )

    assert "# workstack create - cd to new worktree" in script
    assert f"cd '{worktree_path}'" in script
    assert 'echo "✓ Switched to new worktree."' in script


def test_create_with_script_flag() -> None:
    """Test that --script flag outputs cd script instead of regular messages."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure FakeGitOps with root worktree only
        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            default_branches={env.root_worktree: "main"},
        )

        # Create test context using env.build_context() helper
        test_ctx = env.build_context(git_ops=git_ops)

        # Run workstack create with --script flag
        result = runner.invoke(
            cli, ["create", "test-worktree", "--no-post", "--script"], obj=test_ctx
        )
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify worktree was created
        worktree_path = env.workstacks_root / "repo" / "test-worktree"
        assert worktree_path.exists()

        # Output should be a temp file path
        script_path = Path(result.output.strip())
        assert script_path.exists()
        assert script_path.name.startswith("workstack-create-")
        assert script_path.name.endswith(".sh")

        # Verify script content contains the cd command
        script_content = script_path.read_text(encoding="utf-8")
        expected_script = render_cd_script(
            worktree_path,
            comment="cd to new worktree",
            success_message="✓ Switched to new worktree.",
        ).strip()
        assert expected_script in script_content

        # Cleanup
        script_path.unlink(missing_ok=True)


def test_hidden_shell_cmd_create_passthrough_on_help() -> None:
    """Shell integration command signals passthrough for help."""
    runner = CliRunner()
    result = runner.invoke(hidden_shell_cmd, ["create", "--help"])

    assert result.exit_code == 0
    assert result.output.strip() == "__WORKSTACK_PASSTHROUGH__"


def test_hidden_shell_cmd_create_passthrough_on_error(tmp_path: Path) -> None:
    """Shell integration command signals passthrough for errors."""
    # Set up isolated environment without workstack config
    # This ensures create_context() won't find a real repo
    env_vars = os.environ.copy()
    env_vars["HOME"] = str(tmp_path)

    runner = CliRunner(env=env_vars)

    # Create isolated filesystem without git repo or config
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Try to create without any setup - should error
        result = runner.invoke(hidden_shell_cmd, ["create", "test-worktree"])

        # Should passthrough on error
        assert result.exit_code != 0
        assert result.output.strip() == "__WORKSTACK_PASSTHROUGH__"
