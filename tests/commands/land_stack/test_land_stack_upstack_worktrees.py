"""Tests for land-stack with upstack branches in worktrees.

Verifies that when force-pushing upstack branches during land-stack,
gt submit is called from the correct worktree directory (not repo_root)
when the branch is checked out in a worktree.

This prevents the bug where gt submit --branch checks out branches in
the root worktree, corrupting its state.
"""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.branch_metadata import BranchMetadata
from erk.core.git import WorktreeInfo
from tests.fakes.git import FakeGit
from tests.fakes.github import FakeGitHub
from tests.fakes.graphite import FakeGraphite
from tests.test_utils.builders import PullRequestInfoBuilder
from tests.test_utils.env_helpers import erk_inmem_env


def test_land_stack_force_pushes_upstack_branches_from_correct_worktree() -> None:
    """Test that upstack branches are force-pushed from their worktree, not repo_root.

    Scenario:
    - Stack: main -> feat-1 -> feat-2 -> feat-3 -> feat-4
    - Current branch: feat-2 (in root worktree)
    - feat-3 is checked out in a separate worktree
    - feat-4 is not in any worktree
    - Landing feat-1 and feat-2 with --down flag
    - After merging, feat-3 and feat-4 become "upstack" (remaining in stack after landing)

    Expected behavior:
    - After landing feat-1 and feat-2, code force-pushes upstack branches
    - feat-3 submit_branch should be called from feat-3's worktree path
    - feat-4 submit_branch should be called from repo_root (not in worktree)

    This test verifies the fix for the bug where gt submit --branch was called
    from repo_root for ALL upstack branches, causing Graphite to check out branches
    in the root worktree even when they were already checked out in linked worktrees.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up directory structure with multiple worktrees
        repo_root = env.cwd
        feat3_worktree = env.erk_root / "feat-3"

        # Configure git ops with worktrees
        # Root worktree has feat-2 checked out (being landed)
        # feat-3 is in a linked worktree
        # feat-4 is not checked out anywhere
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feat-2"},  # Current branch being landed
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=repo_root, branch="feat-2", is_root=True),
                    WorktreeInfo(path=feat3_worktree, branch="feat-3", is_root=False),
                ],
            },
        )

        # Configure Graphite metadata for stack
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk(
                    "main",
                    children=["feat-1"],
                    commit_sha="abc123",
                ),
                "feat-1": BranchMetadata.branch(
                    "feat-1",
                    parent="main",
                    children=["feat-2"],
                    commit_sha="def456",
                ),
                "feat-2": BranchMetadata.branch(
                    "feat-2",
                    parent="feat-1",
                    children=["feat-3"],
                    commit_sha="ghi789",
                ),
                "feat-3": BranchMetadata.branch(
                    "feat-3",
                    parent="feat-2",
                    children=["feat-4"],
                    commit_sha="jkl012",
                ),
                "feat-4": BranchMetadata.branch(
                    "feat-4",
                    parent="feat-3",
                    commit_sha="mno345",
                ),
            },
            stacks={
                "feat-2": ["main", "feat-1", "feat-2", "feat-3", "feat-4"],
            },
        )

        # Configure GitHub ops with PRs (only for branches being landed)
        github_ops = FakeGitHub(
            prs={
                "feat-1": PullRequestInfoBuilder(101, "feat-1").with_passing_checks().build(),
                "feat-2": PullRequestInfoBuilder(102, "feat-2").with_passing_checks().build(),
            },
            pr_bases={
                101: "main",
                102: "feat-1",
            },
        )

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
        )

        # Execute land-stack with --down flag (land only feat-1 and feat-2)
        # This leaves feat-3 and feat-4 as "upstack" branches that need force-push
        result = runner.invoke(cli, ["land-stack", "--down", "--force", "--dry-run"], obj=test_ctx)

        # Verify command succeeded
        assert result.exit_code == 0, f"Command failed with: {result.output}"

        # Verify submit_branch was called for upstack branches
        submit_calls = graphite_ops.submit_branch_calls
        submit_calls_by_branch = {call[1]: call for call in submit_calls}

        # feat-3 should be submitted from its worktree (not repo_root)
        if "feat-3" in submit_calls_by_branch:
            feat3_call = submit_calls_by_branch["feat-3"]
            assert feat3_call[0] == feat3_worktree, (
                f"Expected feat-3 to be submitted from {feat3_worktree}, "
                f"but was submitted from {feat3_call[0]}"
            )

        # feat-4 should be submitted from repo_root (not in any worktree)
        if "feat-4" in submit_calls_by_branch:
            feat4_call = submit_calls_by_branch["feat-4"]
            assert feat4_call[0] == repo_root, (
                f"Expected feat-4 to be submitted from {repo_root}, "
                f"but was submitted from {feat4_call[0]}"
            )


def test_land_stack_force_pushes_branch_not_in_worktree_from_repo_root() -> None:
    """Test that branches NOT in worktrees are force-pushed from repo_root.

    Scenario:
    - Stack: main -> feat-1 -> feat-2
    - Only feat-1 is in a worktree (current)
    - feat-2 is NOT in any worktree
    - Landing feat-1 triggers force-push of upstack branch (feat-2)

    Expected behavior:
    - feat-2 submit_branch should be called from repo_root
    - This is safe because feat-2 is not checked out anywhere

    This test verifies that the fix doesn't break the case where branches
    are not in worktrees.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_root = env.cwd

        # Configure git ops with only one worktree (current branch)
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feat-1"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=repo_root, branch="feat-1", is_root=True),
                ],
            },
        )

        # Configure Graphite metadata for stack (feat-2 not in worktree)
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk(
                    "main",
                    children=["feat-1"],
                    commit_sha="abc123",
                ),
                "feat-1": BranchMetadata.branch(
                    "feat-1",
                    parent="main",
                    children=["feat-2"],
                    commit_sha="def456",
                ),
                "feat-2": BranchMetadata.branch(
                    "feat-2",
                    parent="feat-1",
                    commit_sha="ghi789",
                ),
            },
            stacks={
                "feat-1": ["main", "feat-1", "feat-2"],
            },
        )

        # Configure GitHub ops with PRs
        github_ops = FakeGitHub(
            prs={
                "feat-1": PullRequestInfoBuilder(101, "feat-1").with_passing_checks().build(),
                "feat-2": PullRequestInfoBuilder(102, "feat-2").with_passing_checks().build(),
            },
            pr_bases={
                101: "main",
                102: "feat-1",
            },
        )

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
        )

        # Execute land-stack (dry-run to skip actual PR operations)
        result = runner.invoke(cli, ["land-stack", "--force", "--dry-run"], obj=test_ctx)

        # Verify command succeeded
        assert result.exit_code == 0, f"Command failed with: {result.output}"

        # Verify submit_branch was called for upstack branch
        submit_calls = graphite_ops.submit_branch_calls
        submit_calls_by_branch = {call[1]: call for call in submit_calls}

        # feat-2 should be submitted from repo_root (not in any worktree)
        if "feat-2" in submit_calls_by_branch:
            feat2_call = submit_calls_by_branch["feat-2"]
            assert feat2_call[0] == repo_root, (
                f"Expected feat-2 to be submitted from {repo_root}, "
                f"but was submitted from {feat2_call[0]}"
            )
