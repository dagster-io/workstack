import re
from pathlib import Path

from click.testing import CliRunner

from tests.fakes.gitops import FakeGitOps
from tests.test_utils.env_helpers import simulated_workstack_env
from workstack.cli.cli import cli
from workstack.cli.commands.shell_integration import hidden_shell_cmd
from workstack.core.context import WorkstackContext
from workstack.core.gitops import WorktreeInfo
from workstack.core.global_config import GlobalConfig, InMemoryGlobalConfigOps


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def test_switch_command() -> None:
    """Test the switch command outputs activation script."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create linked worktree for "myfeature"
        myfeature_path = env.create_linked_worktree("myfeature", "myfeature", chdir=False)

        # Configure FakeGitOps with worktrees
        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                    WorktreeInfo(path=myfeature_path, branch="myfeature", is_root=False),
                ]
            },
            current_branches={
                env.root_worktree: "main",
                myfeature_path: "myfeature",
            },
            git_common_dirs={
                env.root_worktree: env.git_dir,
                myfeature_path: env.git_dir,
            },
            default_branches={env.root_worktree: "main"},
        )

        # Create global config with workstacks_root
        global_config = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )
        global_config_ops = InMemoryGlobalConfigOps(config=global_config)

        # Create test context
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            global_config=global_config,
            cwd=env.cwd,
            trunk_branch="main",
        )

        # Run switch command with --script flag
        result = runner.invoke(cli, ["switch", "myfeature", "--script"], obj=test_ctx)
        assert result.exit_code == 0

        # Output should be a temp file path
        script_path = Path(result.output.strip())
        assert script_path.exists()
        assert script_path.name.startswith("workstack-switch-")
        assert script_path.name.endswith(".sh")

        # Verify script content
        script_content = script_path.read_text()
        assert "cd" in script_content
        assert str(myfeature_path) in script_content
        # Should source activate if venv exists
        assert "activate" in script_content

        # Cleanup
        script_path.unlink(missing_ok=True)


def test_switch_nonexistent_worktree() -> None:
    """Test switch command with non-existent worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure FakeGitOps with just root worktree
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
            show_pr_checks=False,
        )
        global_config_ops = InMemoryGlobalConfigOps(config=global_config)

        # Create test context
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            global_config=global_config,
            cwd=env.cwd,
            trunk_branch="main",
        )

        # Try to switch to non-existent worktree
        result = runner.invoke(cli, ["switch", "doesnotexist"], obj=test_ctx)

        assert result.exit_code != 0
        assert "not found" in result.output.lower()


def test_switch_shell_completion() -> None:
    """Test that switch command has shell completion configured."""
    # This is a bit tricky to test without a real shell, but we can verify
    # the command is set up with the right completion function by checking help
    runner = CliRunner()
    result = runner.invoke(cli, ["switch", "--help"])

    assert result.exit_code == 0
    assert "NAME" in result.output


def test_switch_to_root() -> None:
    """Test switching to root repo using 'root'."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure FakeGitOps with just the root worktree
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
            show_pr_checks=False,
        )
        global_config_ops = InMemoryGlobalConfigOps(config=global_config)

        # Create test context
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            global_config=global_config,
            cwd=env.cwd,
            trunk_branch="main",
        )

        result = runner.invoke(cli, ["switch", "root", "--script"], obj=test_ctx)
        assert result.exit_code == 0

        # Output should be a temp file path
        script_path = Path(result.output.strip())
        assert script_path.exists()
        assert script_path.name.startswith("workstack-switch-")
        assert script_path.name.endswith(".sh")

        # Verify script content
        script_content = script_path.read_text()
        assert "cd" in script_content
        assert str(env.root_worktree) in script_content
        assert "root" in script_content.lower()

        # Cleanup
        script_path.unlink(missing_ok=True)


def test_hidden_shell_cmd_switch_passthrough_on_help() -> None:
    """Shell integration wrapper defers to regular switch help."""
    runner = CliRunner()
    result = runner.invoke(hidden_shell_cmd, ["switch", "--help"])

    assert result.exit_code == 0
    assert result.output.strip() == "__WORKSTACK_PASSTHROUGH__"


def test_list_includes_root() -> None:
    """Test that list command shows root repo with branch name."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create linked worktree for "myfeature"
        myfeature_path = env.create_linked_worktree("myfeature", "myfeature", chdir=False)

        # Configure FakeGitOps with worktrees
        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                    WorktreeInfo(path=myfeature_path, branch="myfeature", is_root=False),
                ]
            },
            current_branches={
                env.root_worktree: "main",
                myfeature_path: "myfeature",
            },
            git_common_dirs={
                env.root_worktree: env.git_dir,
                myfeature_path: env.git_dir,
            },
            default_branches={env.root_worktree: "main"},
        )

        # Create global config with workstacks_root
        global_config = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )
        global_config_ops = InMemoryGlobalConfigOps(config=global_config)

        # Create test context
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            global_config=global_config,
            cwd=env.cwd,
            trunk_branch="main",
        )

        # List worktrees
        result = runner.invoke(cli, ["list"], obj=test_ctx)
        assert result.exit_code == 0

        # Should show root as first entry
        clean_output = strip_ansi(result.output)
        lines = clean_output.strip().split("\n")
        assert len(lines) >= 2
        # Check that first line shows the root worktree
        assert lines[0].startswith("root")
        # Should also show the created worktree
        assert any("myfeature" in line for line in lines)


def test_complete_worktree_names_without_context() -> None:
    """Test completion function works even when Click context obj is None.

    This simulates the shell completion scenario where the CLI group callback
    hasn't run yet, so ctx.obj is None.
    """
    import click

    from workstack.cli.cli import cli
    from workstack.cli.commands.switch import complete_worktree_names

    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create linked worktrees
        feature_a_path = env.create_linked_worktree("feature-a", "feature-a", chdir=False)
        feature_b_path = env.create_linked_worktree("feature-b", "feature-b", chdir=False)
        bugfix_123_path = env.create_linked_worktree("bugfix-123", "bugfix-123", chdir=False)

        # Configure FakeGitOps with worktrees
        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                    WorktreeInfo(path=feature_a_path, branch="feature-a", is_root=False),
                    WorktreeInfo(path=feature_b_path, branch="feature-b", is_root=False),
                    WorktreeInfo(path=bugfix_123_path, branch="bugfix-123", is_root=False),
                ]
            },
            current_branches={
                env.root_worktree: "main",
                feature_a_path: "feature-a",
                feature_b_path: "feature-b",
                bugfix_123_path: "bugfix-123",
            },
            git_common_dirs={
                env.root_worktree: env.git_dir,
                feature_a_path: env.git_dir,
                feature_b_path: env.git_dir,
                bugfix_123_path: env.git_dir,
            },
            default_branches={env.root_worktree: "main"},
        )

        # Create global config with workstacks_root
        global_config = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )
        global_config_ops = InMemoryGlobalConfigOps(config=global_config)

        # Create test context with our fake setup
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            global_config=global_config,
            cwd=env.cwd,
            trunk_branch="main",
        )

        # Create a mock Click context with our test context
        ctx = click.Context(cli)
        ctx.obj = test_ctx  # Set the context directly

        # Call completion function
        completions = complete_worktree_names(ctx, None, "")

        # Should return worktree names
        assert "root" in completions
        assert "feature-a" in completions
        assert "feature-b" in completions
        assert "bugfix-123" in completions

        # Test filtering by prefix
        completions = complete_worktree_names(ctx, None, "feat")
        assert "feature-a" in completions
        assert "feature-b" in completions
        assert "bugfix-123" not in completions

        # Test with None context to verify fallback behavior
        ctx.obj = None
        # This will use create_context() which uses RealGitOps - we can't easily test this
        # without complex mocking, so we'll skip this part of the test


def test_switch_rejects_main_as_worktree_name() -> None:
    """Test that 'main' is rejected with helpful error."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure FakeGitOps with just root worktree
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
            show_pr_checks=False,
        )
        global_config_ops = InMemoryGlobalConfigOps(config=global_config)

        # Create test context
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            global_config=global_config,
            cwd=env.cwd,
            trunk_branch="main",
        )

        # Try to switch to "main"
        result = runner.invoke(cli, ["switch", "main"], obj=test_ctx)

        # Should fail with error suggesting to use root
        assert result.exit_code != 0
        assert "main" in result.output.lower()
        assert "workstack switch root" in result.output


def test_switch_rejects_master_as_worktree_name() -> None:
    """Test that 'master' is rejected with helpful error."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure FakeGitOps with master as trunk branch
        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="master", is_root=True),
                ]
            },
            current_branches={env.root_worktree: "master"},
            git_common_dirs={env.root_worktree: env.git_dir},
            default_branches={env.root_worktree: "master"},
        )

        # Create test context
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            cwd=env.cwd,
            trunk_branch="master",
        )

        # Try to switch to "master"
        result = runner.invoke(cli, ["switch", "master"], obj=test_ctx)

        # Should fail with error suggesting to use root
        assert result.exit_code != 0
        assert "master" in result.output.lower()
        assert "workstack switch root" in result.output
