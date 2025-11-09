"""Tests for workstack jump command."""

from pathlib import Path

from click.testing import CliRunner

from tests.commands.graphite.test_land_stack import (
    simulated_workstack_env,
)
from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.global_config_ops import FakeGlobalConfigOps
from tests.fakes.shell_ops import FakeShellOps
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext


def test_jump_to_branch_in_single_worktree() -> None:
    """Test jumping to a branch that is checked out in exactly one worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create worktree directories
        feature_wt = env.create_linked_worktree("feature-wt", "feature-2", chdir=False)
        env.create_linked_worktree("other-wt", "other-feature", chdir=False)

        # Build ops with other-feature as current branch
        # Note: jump doesn't use graphite, so we can pass empty branches dict
        from tests.fakes.gitops import FakeGitOps
        from tests.fakes.graphite_ops import FakeGraphiteOps
        from workstack.core.gitops import WorktreeInfo

        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-2", is_root=False),
                    WorktreeInfo(
                        path=env.root_worktree.parent / "workstacks" / "repo" / "other-wt",
                        branch="other-feature",
                        is_root=False,
                    ),
                ]
            },
            current_branches={env.root_worktree: "other-feature"},
            default_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.root_worktree / ".git"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.root_worktree.parent / "workstacks",
            use_graphite=False,  # No longer requires Graphite
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        # Jump to feature-2 which is checked out in feature_wt
        result = runner.invoke(
            cli, ["jump", "feature-2", "--script"], obj=test_ctx, catch_exceptions=False
        )

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Should not checkout (already on the branch)
        assert len(git_ops.checked_out_branches) == 0
        # Should generate activation script
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text()
        assert str(feature_wt) in script_content


def test_jump_to_branch_not_found() -> None:
    """Test jumping to a branch that is not checked out in any worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create worktree for feature-1
        env.create_linked_worktree("feature-1-wt", "feature-1", chdir=False)

        # Build ops manually since jump doesn't use graphite
        from tests.fakes.gitops import FakeGitOps
        from tests.fakes.graphite_ops import FakeGraphiteOps
        from workstack.core.gitops import WorktreeInfo

        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                    WorktreeInfo(
                        path=env.root_worktree.parent / "workstacks" / "repo" / "feature-1-wt",
                        branch="feature-1",
                        is_root=False,
                    ),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.root_worktree / ".git"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.root_worktree.parent / "workstacks",
            use_graphite=False,  # No longer requires Graphite
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        # Jump to a branch that doesn't exist
        result = runner.invoke(
            cli, ["jump", "nonexistent-branch"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "is not checked out in any worktree" in result.stderr
        assert "workstack create --from-branch nonexistent-branch" in result.stderr


def test_jump_to_branch_in_stack_but_not_checked_out() -> None:
    """Test that jump fails when branch exists in repo but is not checked out.

    With exact-match behavior, branches that exist in Graphite stacks but are not
    directly checked out should fail with appropriate error message.
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create worktree for feature-1 only
        wt1 = env.create_linked_worktree("feature-1-wt", "feature-1", chdir=False)

        # Build ops manually
        from tests.fakes.gitops import FakeGitOps
        from tests.fakes.graphite_ops import FakeGraphiteOps
        from workstack.core.gitops import WorktreeInfo

        # feature-1 is checked out, but feature-base is not
        # (even though it might exist in the stack)
        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                    WorktreeInfo(path=wt1, branch="feature-1", is_root=False),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.root_worktree / ".git"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.root_worktree.parent / "workstacks",
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

        # Jump to feature-base which exists in repo but is not checked out in any worktree
        result = runner.invoke(cli, ["jump", "feature-base"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "is not checked out in any worktree" in result.stderr


def test_jump_works_without_graphite() -> None:
    """Test that jump works without Graphite enabled."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        feature_wt = env.create_linked_worktree("feature-1-wt", "feature-1", chdir=False)

        from tests.fakes.gitops import FakeGitOps
        from tests.fakes.graphite_ops import FakeGraphiteOps
        from workstack.core.gitops import WorktreeInfo

        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-1", is_root=False),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.root_worktree / ".git"},
        )

        # Graphite is NOT enabled - jump should still work
        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.root_worktree.parent / "workstacks",
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
            cli, ["jump", "feature-1", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Should succeed - jump no longer requires Graphite
        assert result.exit_code == 0
        script_path = Path(result.stdout.strip())
        assert script_path.exists()


def test_jump_already_on_target_branch() -> None:
    """Test jumping when the target branch is already checked out in a single worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        feature_wt = env.create_linked_worktree("feature-1-wt", "feature-1", chdir=False)
        other_wt = env.create_linked_worktree("other-wt", "other-feature", chdir=False)

        from tests.fakes.gitops import FakeGitOps
        from tests.fakes.graphite_ops import FakeGraphiteOps
        from workstack.core.gitops import WorktreeInfo

        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=other_wt, branch="other-feature", is_root=False),
                    # Already on feature-1
                    WorktreeInfo(path=feature_wt, branch="feature-1", is_root=False),
                ]
            },
            current_branches={env.root_worktree: "other-feature"},
            git_common_dirs={env.root_worktree: env.root_worktree / ".git"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.root_worktree.parent / "workstacks",
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

        # Jump to feature-1 which is already checked out
        result = runner.invoke(
            cli, ["jump", "feature-1", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Should succeed without checking out (already on the branch)
        assert result.exit_code == 0
        # Should not have checked out (it's already checked out)
        assert len(git_ops.checked_out_branches) == 0


def test_jump_succeeds_when_branch_exactly_checked_out() -> None:
    """Test that jump succeeds when branch is exactly checked out in a worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        feature_wt = env.create_linked_worktree("feature-wt", "feature-2", chdir=False)
        other_wt = env.create_linked_worktree("other-wt", "other-feature", chdir=False)

        from tests.fakes.gitops import FakeGitOps
        from tests.fakes.graphite_ops import FakeGraphiteOps
        from workstack.core.gitops import WorktreeInfo

        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=other_wt, branch="other-feature", is_root=False),
                    # feature-2 is checked out
                    WorktreeInfo(path=feature_wt, branch="feature-2", is_root=False),
                ]
            },
            current_branches={env.root_worktree: "other-feature"},
            git_common_dirs={env.root_worktree: env.root_worktree / ".git"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.root_worktree.parent / "workstacks",
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

        # Jump to feature-2 which is checked out in feature_wt
        result = runner.invoke(
            cli, ["jump", "feature-2", "--script"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        # Should not checkout (already on feature-2)
        assert len(git_ops.checked_out_branches) == 0
        # Should generate activation script
        script_path = Path(result.stdout.strip())
        assert script_path.exists()


def test_jump_with_multiple_worktrees_same_branch() -> None:
    """Test error when multiple worktrees have the same branch checked out.

    This is an edge case that shouldn't happen in normal use (git prevents it),
    but our code should handle it gracefully.
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        wt1 = env.create_linked_worktree("wt1", "feature-2", chdir=False)
        wt2 = env.create_linked_worktree("wt2", "feature-2", chdir=False)

        from tests.fakes.gitops import FakeGitOps
        from tests.fakes.graphite_ops import FakeGraphiteOps
        from workstack.core.gitops import WorktreeInfo

        # Edge case: same branch checked out in multiple worktrees
        # (shouldn't happen in real git, but test our handling)
        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=wt1, branch="feature-2", is_root=False),
                    WorktreeInfo(path=wt2, branch="feature-2", is_root=False),  # Same branch
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.root_worktree / ".git"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.root_worktree.parent / "workstacks",
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

        # Jump to feature-2 which is checked out in multiple worktrees
        result = runner.invoke(
            cli, ["jump", "feature-2", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Should show error about multiple worktrees
        assert result.exit_code == 1
        assert "exists in multiple worktrees" in result.stderr
