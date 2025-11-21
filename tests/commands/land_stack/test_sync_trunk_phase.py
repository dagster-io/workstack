"""Tests for _execute_sync_trunk_phase() in land-stack execution.

Tests verify that trunk sync works correctly when trunk is checked out in a worktree.
This is a regression test for the bug where trunk was not updated after landing PRs.
"""

from click.testing import CliRunner

from erk.cli.commands.land_stack.execution import _execute_sync_trunk_phase
from erk.core.git.abc import WorktreeInfo
from tests.fakes.git import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env


def test_sync_trunk_in_worktree_pulls_at_worktree_location() -> None:
    """Test that trunk sync pulls in the correct worktree when trunk is checked out there.

    This is the main bug fix test: when trunk is checked out in a worktree,
    pull_branch should be called with the worktree path, not repo_root.
    """
    # Arrange: Set up trunk checked out in a worktree
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        trunk_worktree = env.erk_root / "worktrees" / "main"
        feature_branch = "feat-1"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch=feature_branch, is_root=True),
                    WorktreeInfo(path=trunk_worktree, branch="main", is_root=False),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: feature_branch},
            existing_paths={env.cwd, trunk_worktree},
        )

        ctx = env.build_context(git=git_ops)

        # Act: Execute trunk sync phase
        _execute_sync_trunk_phase(
            ctx=ctx,
            repo_root=env.cwd,
            parent="main",
            script_mode=False,
        )

        # Assert: Should have fetched main
        assert ("origin", "main") in git_ops.fetched_branches

        # Assert: Should have pulled main in the WORKTREE location, not repo_root
        pulled = git_ops.pulled_branches
        assert len(pulled) == 1, f"Expected 1 pull, got {len(pulled)}: {pulled}"

        remote, branch, ff_only = pulled[0]
        assert remote == "origin"
        assert branch == "main"
        assert ff_only is True

        # The key assertion: pull should NOT have happened at repo_root
        # (we can't directly verify the path with current FakeGit, but we can
        # verify that checkout was NOT called, which would indicate the old buggy behavior)
        assert len(git_ops.checked_out_branches) == 0, (
            "Should not checkout branches when trunk is already in a worktree"
        )


def test_sync_trunk_not_checked_out_uses_repo_root() -> None:
    """Test that trunk sync checks out and pulls in repo_root when trunk is not checked out.

    This is a regression test: ensures the non-worktree case still works correctly.
    """
    # Arrange: Set up trunk NOT checked out anywhere
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        feature_branch = "feat-1"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch=feature_branch, is_root=True),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: feature_branch},
            existing_paths={env.cwd},
        )

        ctx = env.build_context(git=git_ops)

        # Act: Execute trunk sync phase
        _execute_sync_trunk_phase(
            ctx=ctx,
            repo_root=env.cwd,
            parent="main",
            script_mode=False,
        )

        # Assert: Should have fetched main
        assert ("origin", "main") in git_ops.fetched_branches

        # Assert: Should have checked out main in repo_root
        assert (env.cwd, "main") in git_ops.checked_out_branches

        # Assert: Should have pulled main
        pulled = git_ops.pulled_branches
        assert len(pulled) == 1
        remote, branch, ff_only = pulled[0]
        assert remote == "origin"
        assert branch == "main"
        assert ff_only is True

        # Assert: Should have checked out trunk only (NOT feature branch)
        # After fix, we only checkout trunk once - no second checkout to "restore" feature branch
        checkouts = git_ops.checked_out_branches
        assert len(checkouts) == 1, f"Expected 1 checkout (main only), got {len(checkouts)}"
        assert checkouts[0] == (env.cwd, "main")
        # No second checkout to feature branch - this was the bug


def test_sync_trunk_in_root_worktree_still_pulls() -> None:
    """Test that trunk sync works when trunk is checked out in the root worktree.

    Edge case: trunk is checked out in the root worktree (repo_root), not a linked worktree.
    This should behave like the worktree case - pull in place without checkout.
    """
    # Arrange: Set up trunk checked out in root worktree
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            existing_paths={env.cwd},
        )

        ctx = env.build_context(git=git_ops)

        # Act: Execute trunk sync phase
        _execute_sync_trunk_phase(
            ctx=ctx,
            repo_root=env.cwd,
            parent="main",
            script_mode=False,
        )

        # Assert: Should have fetched main
        assert ("origin", "main") in git_ops.fetched_branches

        # Assert: Should have pulled main in place (trunk is already checked out at repo_root)
        pulled = git_ops.pulled_branches
        assert len(pulled) == 1

        # Assert: Should NOT have checked out (already on correct branch)
        # Since trunk is already checked out at repo_root, we should pull in place
        assert len(git_ops.checked_out_branches) == 0


def test_sync_trunk_leaves_root_on_trunk_not_feature_branch() -> None:
    """Regression test: trunk sync should NOT checkout feature branch at root worktree.

    This is the key bug fix: after syncing trunk, the root worktree should stay on trunk,
    not be checked out to the feature branch being landed. Checking out the feature branch
    at root causes "branch checked out in multiple worktrees" errors on subsequent lands.

    Bug context:
    - On 2025-11-20, session-log-preprocessing-kit-25-11-20 was incorrectly checked out
      at /Users/schrockn/code/erk (root worktree) during land-stack operation
    - This blocked actual landing because git doesn't allow same branch in multiple worktrees
    - Root cause: lines 183-186 in execution.py tried to "restore" feature branch at root
    """
    # Arrange: Set up scenario that triggers the buggy code path
    # CRITICAL: Root worktree must be on the FEATURE branch, NOT trunk
    # This forces the code into the else block (line 179-186) where the bug exists
    # - Root worktree on feature branch (session-log-preprocessing-kit-25-11-20)
    # - Trunk (main) is NOT checked out anywhere
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        feature_branch = "session-log-preprocessing-kit-25-11-20"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch=feature_branch, is_root=True),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: feature_branch},
            existing_paths={env.cwd},
        )

        ctx = env.build_context(git=git_ops)

        # Act: Execute trunk sync phase for feature branch
        _execute_sync_trunk_phase(
            ctx=ctx,
            repo_root=env.cwd,
            parent="main",
            script_mode=False,
        )

        # Assert: Should have fetched and pulled main
        assert ("origin", "main") in git_ops.fetched_branches
        pulled = git_ops.pulled_branches
        assert len(pulled) == 1
        remote, branch, ff_only = pulled[0]
        assert remote == "origin"
        assert branch == "main"

        # CRITICAL ASSERTION: Root worktree should stay on trunk, NOT checkout feature branch
        # The bug was that lines 183-186 would checkout the feature branch here
        checkouts = git_ops.checked_out_branches
        for path, checked_out_branch in checkouts:
            assert checked_out_branch != feature_branch, (
                f"BUG: Feature branch '{feature_branch}' was checked out at {path}. "
                f"Root worktree should stay on trunk, not switch to feature branch. "
                f"This causes 'branch checked out in multiple worktrees' errors."
            )
