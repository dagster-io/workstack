"""Integration tests for git operations.

These tests verify that RealGitOps correctly handles git operations with real git repositories.
Integration tests use actual git subprocess calls to validate the abstractions.
"""

import subprocess
from pathlib import Path

import pytest

from tests.integration.conftest import (
    GitOpsSetup,
    GitOpsWithDetached,
    GitOpsWithExistingBranch,
    GitOpsWithWorktrees,
)


def test_list_worktrees_single_repo(git_ops: GitOpsSetup) -> None:
    """Test listing worktrees returns only main repository when no worktrees exist."""
    worktrees = git_ops.git_ops.list_worktrees(git_ops.repo)

    assert len(worktrees) == 1
    assert worktrees[0].path == git_ops.repo
    assert worktrees[0].branch == "main"


def test_list_worktrees_multiple(git_ops_with_worktrees: GitOpsWithWorktrees) -> None:
    """Test listing worktrees with multiple worktrees."""
    worktrees = git_ops_with_worktrees.git_ops.list_worktrees(git_ops_with_worktrees.repo)

    assert len(worktrees) == 3

    # Find each worktree
    main_wt = next(wt for wt in worktrees if wt.branch == "main")
    feat1_wt = next(wt for wt in worktrees if wt.branch == "feature-1")
    feat2_wt = next(wt for wt in worktrees if wt.branch == "feature-2")

    assert main_wt.path == git_ops_with_worktrees.repo
    assert feat1_wt.path == git_ops_with_worktrees.worktrees[0]
    assert feat2_wt.path == git_ops_with_worktrees.worktrees[1]


def test_list_worktrees_detached_head(git_ops_with_detached: GitOpsWithDetached) -> None:
    """Test listing worktrees includes detached HEAD worktree with None branch."""
    worktrees = git_ops_with_detached.git_ops.list_worktrees(git_ops_with_detached.repo)

    assert len(worktrees) == 2
    detached_wt = next(wt for wt in worktrees if wt.path == git_ops_with_detached.detached_wt)
    assert detached_wt.branch is None


def test_get_current_branch_normal(git_ops: GitOpsSetup) -> None:
    """Test getting current branch in normal checkout."""
    branch = git_ops.git_ops.get_current_branch(git_ops.repo)

    assert branch == "main"


def test_get_current_branch_after_checkout(git_ops: GitOpsSetup) -> None:
    """Test getting current branch after checking out a different branch."""
    # Create and checkout new branch
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=git_ops.repo, check=True)

    branch = git_ops.git_ops.get_current_branch(git_ops.repo)

    assert branch == "feature"


def test_get_current_branch_detached_head(git_ops: GitOpsSetup) -> None:
    """Test getting current branch in detached HEAD state returns None."""
    # Get commit hash and checkout in detached state
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=git_ops.repo,
        capture_output=True,
        text=True,
        check=True,
    )
    commit_hash = result.stdout.strip()
    subprocess.run(["git", "checkout", commit_hash], cwd=git_ops.repo, check=True)

    branch = git_ops.git_ops.get_current_branch(git_ops.repo)

    assert branch is None


def test_get_current_branch_non_git_directory(git_ops: GitOpsSetup, tmp_path: Path) -> None:
    """Test getting current branch in non-git directory returns None."""
    non_git = tmp_path / "not-a-repo"
    non_git.mkdir()

    branch = git_ops.git_ops.get_current_branch(non_git)

    assert branch is None


def test_detect_default_branch_main(git_ops: GitOpsSetup) -> None:
    """Test detecting default branch when it's main."""
    default_branch = git_ops.git_ops.detect_default_branch(git_ops.repo)

    assert default_branch == "main"


def test_detect_default_branch_master(
    tmp_path: Path,
) -> None:
    """Test detecting default branch when it's master using real git."""
    from tests.integration.conftest import init_git_repo
    from workstack.core.gitops import RealGitOps

    repo = tmp_path / "repo"
    repo.mkdir()

    # Create real repo with master branch
    init_git_repo(repo, "master")
    git_ops = RealGitOps()

    default_branch = git_ops.detect_default_branch(repo)

    assert default_branch == "master"


def test_detect_default_branch_with_remote_head(
    tmp_path: Path,
) -> None:
    """Test detecting default branch using remote HEAD with real git."""
    from tests.integration.conftest import init_git_repo
    from workstack.core.gitops import RealGitOps

    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    # Set up remote HEAD manually
    subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"],
        cwd=repo,
        check=True,
    )

    git_ops = RealGitOps()

    default_branch = git_ops.detect_default_branch(repo)

    assert default_branch == "main"


def test_detect_default_branch_neither_exists(
    tmp_path: Path,
) -> None:
    """Test default branch detection when neither main nor master exist using real git."""
    from tests.integration.conftest import init_git_repo
    from workstack.core.gitops import RealGitOps

    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "trunk")

    # Delete the trunk branch we just created (keep the commit)
    subprocess.run(["git", "checkout", "--detach"], cwd=repo, check=True)
    subprocess.run(["git", "branch", "-D", "trunk"], cwd=repo, check=True)

    git_ops = RealGitOps()

    with pytest.raises(SystemExit):
        git_ops.detect_default_branch(repo)


def test_get_git_common_dir_from_main_repo(git_ops: GitOpsSetup) -> None:
    """Test getting git common dir from main repository."""
    git_dir = git_ops.git_ops.get_git_common_dir(git_ops.repo)

    assert git_dir is not None
    assert git_dir == git_ops.repo / ".git"


def test_get_git_common_dir_from_worktree(git_ops_with_worktrees: GitOpsWithWorktrees) -> None:
    """Test getting git common dir from worktree returns shared .git directory."""
    wt = git_ops_with_worktrees.worktrees[0]

    git_dir = git_ops_with_worktrees.git_ops.get_git_common_dir(wt)

    assert git_dir is not None
    assert git_dir == git_ops_with_worktrees.repo / ".git"


def test_get_git_common_dir_non_git_directory(git_ops: GitOpsSetup, tmp_path: Path) -> None:
    """Test getting git common dir in non-git directory returns None."""
    non_git = tmp_path / "not-a-repo"
    non_git.mkdir()

    git_dir = git_ops.git_ops.get_git_common_dir(non_git)

    assert git_dir is None


def test_add_worktree_with_existing_branch(
    git_ops_with_existing_branch: GitOpsWithExistingBranch,
) -> None:
    """Test adding worktree with existing branch."""
    # Create the feature branch
    subprocess.run(
        ["git", "branch", "feature"],
        cwd=git_ops_with_existing_branch.repo,
        check=True,
    )

    git_ops_with_existing_branch.git_ops.add_worktree(
        git_ops_with_existing_branch.repo,
        git_ops_with_existing_branch.wt_path,
        branch="feature",
        ref=None,
        create_branch=False,
    )

    assert git_ops_with_existing_branch.wt_path.exists()

    # Verify branch is checked out
    branch = git_ops_with_existing_branch.git_ops.get_current_branch(
        git_ops_with_existing_branch.wt_path
    )
    assert branch == "feature"


def test_add_worktree_create_new_branch(
    git_ops_with_existing_branch: GitOpsWithExistingBranch,
) -> None:
    """Test adding worktree with new branch creation."""
    git_ops_with_existing_branch.git_ops.add_worktree(
        git_ops_with_existing_branch.repo,
        git_ops_with_existing_branch.wt_path,
        branch="new-feature",
        ref=None,
        create_branch=True,
    )

    assert git_ops_with_existing_branch.wt_path.exists()

    # Verify new branch is checked out
    branch = git_ops_with_existing_branch.git_ops.get_current_branch(
        git_ops_with_existing_branch.wt_path
    )
    assert branch == "new-feature"


def test_add_worktree_from_specific_ref(
    tmp_path: Path,
) -> None:
    """Test adding worktree from specific ref using real git."""
    from tests.integration.conftest import init_git_repo
    from workstack.core.gitops import RealGitOps

    repo = tmp_path / "repo"
    repo.mkdir()
    wt = tmp_path / "wt"

    init_git_repo(repo, "main")

    # Create another commit on main
    (repo / "file.txt").write_text("content\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Add file"], cwd=repo, check=True)

    # Create branch at main
    subprocess.run(["git", "branch", "old-main", "HEAD~1"], cwd=repo, check=True)

    git_ops = RealGitOps()

    git_ops.add_worktree(repo, wt, branch="test-branch", ref="old-main", create_branch=True)

    assert wt.exists()


def test_add_worktree_detached(git_ops_with_existing_branch: GitOpsWithExistingBranch) -> None:
    """Test adding detached worktree."""
    git_ops_with_existing_branch.git_ops.add_worktree(
        git_ops_with_existing_branch.repo,
        git_ops_with_existing_branch.wt_path,
        branch=None,
        ref="HEAD",
        create_branch=False,
    )

    assert git_ops_with_existing_branch.wt_path.exists()

    # Verify it's in detached HEAD state
    branch = git_ops_with_existing_branch.git_ops.get_current_branch(
        git_ops_with_existing_branch.wt_path
    )
    assert branch is None


def test_move_worktree(git_ops_with_worktrees: GitOpsWithWorktrees) -> None:
    """Test moving worktree to new location."""
    old_path = git_ops_with_worktrees.worktrees[0]

    new_base_path = git_ops_with_worktrees.repo.parent / "new"
    new_base_path.mkdir(parents=True, exist_ok=True)

    git_ops_with_worktrees.git_ops.move_worktree(
        git_ops_with_worktrees.repo, old_path, new_base_path
    )

    # Verify old path doesn't exist
    assert not old_path.exists()

    # Verify git still tracks it correctly
    worktrees = git_ops_with_worktrees.git_ops.list_worktrees(git_ops_with_worktrees.repo)
    moved_wt = next(wt for wt in worktrees if wt.branch == "feature-1")
    # Git moves to new/wt1 (subdirectory)
    assert moved_wt.path in [new_base_path, new_base_path / old_path.name]


def test_remove_worktree(git_ops_with_worktrees: GitOpsWithWorktrees) -> None:
    """Test removing worktree."""
    wt = git_ops_with_worktrees.worktrees[0]

    # Ensure worktree directory exists for both implementations
    if not wt.exists():
        wt.mkdir(parents=True, exist_ok=True)

    git_ops_with_worktrees.git_ops.remove_worktree(git_ops_with_worktrees.repo, wt, force=False)

    # Verify it's removed
    worktrees = git_ops_with_worktrees.git_ops.list_worktrees(git_ops_with_worktrees.repo)
    assert len(worktrees) == 2  # Only main and feature-2 remain
    assert worktrees[0].branch == "main"


def test_remove_worktree_with_force(git_ops_with_worktrees: GitOpsWithWorktrees) -> None:
    """Test removing worktree with force flag."""
    wt = git_ops_with_worktrees.worktrees[0]

    # Ensure worktree directory exists
    if not wt.exists():
        wt.mkdir(parents=True, exist_ok=True)

    # Add uncommitted changes
    (wt / "dirty.txt").write_text("uncommitted\n", encoding="utf-8")

    # Remove with force
    git_ops_with_worktrees.git_ops.remove_worktree(git_ops_with_worktrees.repo, wt, force=True)

    # Verify it's removed
    worktrees = git_ops_with_worktrees.git_ops.list_worktrees(git_ops_with_worktrees.repo)
    assert len(worktrees) == 2  # Only main and feature-2 remain
    assert worktrees[0].branch == "main"


def test_checkout_branch(
    tmp_path: Path,
) -> None:
    """Test checking out a branch using real git."""
    from tests.integration.conftest import init_git_repo
    from workstack.core.gitops import RealGitOps

    repo = tmp_path / "repo"
    repo.mkdir()

    init_git_repo(repo, "main")

    # Create a new branch
    subprocess.run(["git", "branch", "feature"], cwd=repo, check=True)

    git_ops = RealGitOps()

    # Checkout the branch
    git_ops.checkout_branch(repo, "feature")

    # Verify branch is checked out
    branch = git_ops.get_current_branch(repo)
    assert branch == "feature"


def test_checkout_branch_in_worktree(
    tmp_path: Path,
) -> None:
    """Test checking out a branch within a worktree using real git."""
    from tests.integration.conftest import init_git_repo
    from workstack.core.gitops import RealGitOps

    repo = tmp_path / "repo"
    repo.mkdir()
    wt = tmp_path / "wt"

    init_git_repo(repo, "main")

    # Create worktree with feature-1
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature-1", str(wt)],
        cwd=repo,
        check=True,
    )

    # Create another branch from the worktree
    subprocess.run(["git", "branch", "feature-2"], cwd=wt, check=True)

    git_ops = RealGitOps()

    # Checkout feature-2 in the worktree
    git_ops.checkout_branch(wt, "feature-2")

    # Verify branch is checked out
    branch = git_ops.get_current_branch(wt)
    assert branch == "feature-2"
