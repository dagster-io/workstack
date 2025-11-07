"""Tests for FakeGitOps test infrastructure.

These tests verify that FakeGitOps correctly simulates git behavior,
tracks mutations, and provides reliable test doubles for CLI tests.
"""

from pathlib import Path

from tests.fakes.gitops import FakeGitOps
from workstack.core.gitops import WorktreeInfo


def test_fake_gitops_list_worktrees() -> None:
    """Test that FakeGitOps lists pre-configured worktrees."""
    repo_root = Path("/repo")
    wt1 = Path("/repo/wt1")
    wt2 = Path("/repo/wt2")

    worktrees = {
        repo_root: [
            WorktreeInfo(path=repo_root, branch="main"),
            WorktreeInfo(path=wt1, branch="feature-1"),
            WorktreeInfo(path=wt2, branch="feature-2"),
        ]
    }

    git_ops = FakeGitOps(worktrees=worktrees)
    result = git_ops.list_worktrees(repo_root)

    assert len(result) == 3
    assert result[0].path == repo_root
    assert result[1].path == wt1
    assert result[2].path == wt2


def test_fake_gitops_add_worktree(tmp_path: Path) -> None:
    """Test that FakeGitOps can add worktrees."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_ops = FakeGitOps()

    new_wt = repo_root / "new-wt"
    git_ops.add_worktree(repo_root, new_wt, branch="new-branch")

    worktrees = git_ops.list_worktrees(repo_root)
    assert len(worktrees) == 1
    assert worktrees[0].path == new_wt
    assert worktrees[0].branch == "new-branch"
    assert new_wt.exists()  # Verify directory was created


def test_fake_gitops_remove_worktree() -> None:
    """Test that FakeGitOps can remove worktrees."""
    repo_root = Path("/repo")
    wt1 = Path("/repo/wt1")

    git_ops = FakeGitOps(
        worktrees={
            repo_root: [
                WorktreeInfo(path=wt1, branch="feature-1"),
            ]
        }
    )

    git_ops.remove_worktree(repo_root, wt1)

    worktrees = git_ops.list_worktrees(repo_root)
    assert len(worktrees) == 0


def test_fake_gitops_get_current_branch() -> None:
    """Test that FakeGitOps returns configured current branch."""
    cwd = Path("/repo")
    git_ops = FakeGitOps(current_branches={cwd: "feature-branch"})

    branch = git_ops.get_current_branch(cwd)
    assert branch == "feature-branch"


def test_fake_gitops_get_default_branch() -> None:
    """Test that FakeGitOps returns configured default branch."""
    repo_root = Path("/repo")
    git_ops = FakeGitOps(default_branches={repo_root: "main"})

    branch = git_ops.detect_default_branch(repo_root)
    assert branch == "main"


def test_fake_gitops_get_git_common_dir() -> None:
    """Test that FakeGitOps returns configured git common dir."""
    cwd = Path("/repo")
    git_dir = Path("/repo/.git")

    git_ops = FakeGitOps(git_common_dirs={cwd: git_dir})

    common_dir = git_ops.get_git_common_dir(cwd)
    assert common_dir == git_dir


def test_fake_gitops_checkout_branch() -> None:
    """Test that FakeGitOps can checkout branches."""
    cwd = Path("/repo")
    git_ops = FakeGitOps(current_branches={cwd: "main"})

    git_ops.checkout_branch(cwd, "feature")

    assert git_ops.get_current_branch(cwd) == "feature"


def test_fake_gitops_delete_branch_tracking() -> None:
    """Test that FakeGitOps tracks deleted branches."""
    repo_root = Path("/repo")
    git_ops = FakeGitOps()

    git_ops.delete_branch_with_graphite(repo_root, "old-branch", force=True)

    assert "old-branch" in git_ops.deleted_branches


def test_fake_gitops_detached_head() -> None:
    """Test FakeGitOps with detached HEAD (None branch)."""
    cwd = Path("/repo")
    git_ops = FakeGitOps(current_branches={cwd: None})

    branch = git_ops.get_current_branch(cwd)
    assert branch is None


def test_fake_gitops_worktree_not_found() -> None:
    """Test FakeGitOps when worktree not found."""
    repo_root = Path("/repo")
    git_ops = FakeGitOps()

    worktrees = git_ops.list_worktrees(repo_root)
    assert len(worktrees) == 0


def test_fake_gitops_has_uncommitted_changes_no_changes() -> None:
    """Test has_uncommitted_changes returns False when no changes."""
    cwd = Path("/repo")
    git_ops = FakeGitOps(file_statuses={cwd: ([], [], [])})

    assert not git_ops.has_uncommitted_changes(cwd)


def test_fake_gitops_has_uncommitted_changes_staged() -> None:
    """Test has_uncommitted_changes returns True when staged changes exist."""
    cwd = Path("/repo")
    git_ops = FakeGitOps(file_statuses={cwd: (["file.txt"], [], [])})

    assert git_ops.has_uncommitted_changes(cwd)


def test_fake_gitops_has_uncommitted_changes_modified() -> None:
    """Test has_uncommitted_changes returns True when modified changes exist."""
    cwd = Path("/repo")
    git_ops = FakeGitOps(file_statuses={cwd: ([], ["file.txt"], [])})

    assert git_ops.has_uncommitted_changes(cwd)


def test_fake_gitops_has_uncommitted_changes_untracked() -> None:
    """Test has_uncommitted_changes returns True when untracked files exist."""
    cwd = Path("/repo")
    git_ops = FakeGitOps(file_statuses={cwd: ([], [], ["file.txt"])})

    assert git_ops.has_uncommitted_changes(cwd)


def test_fake_gitops_has_uncommitted_changes_all_types() -> None:
    """Test has_uncommitted_changes with all types of changes."""
    cwd = Path("/repo")
    git_ops = FakeGitOps(
        file_statuses={cwd: (["staged.txt"], ["modified.txt"], ["untracked.txt"])}
    )

    assert git_ops.has_uncommitted_changes(cwd)


def test_fake_gitops_has_uncommitted_changes_unknown_path() -> None:
    """Test has_uncommitted_changes returns False for unknown path."""
    cwd = Path("/repo")
    git_ops = FakeGitOps()

    assert not git_ops.has_uncommitted_changes(cwd)
