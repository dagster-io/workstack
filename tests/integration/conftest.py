"""Fixtures and helpers for integration tests.

This module provides fixtures that configure git operations implementations
(Real and Fake) for parametrized testing.
"""

import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Literal, NamedTuple

import pytest

from tests.fakes.gitops import FakeGitOps
from workstack.core.gitops import GitOps, RealGitOps, WorktreeInfo


class GitOpsSetup(NamedTuple):
    """Result of git operations setup fixture.

    Attributes:
        git_ops: Either RealGitOps or FakeGitOps (determined by parametrization)
        repo: Path to the repository root (real or mocked)
    """

    git_ops: GitOps
    repo: Path


class GitOpsWithWorktrees(NamedTuple):
    """Result of git operations setup with multiple worktrees.

    Attributes:
        git_ops: Either RealGitOps or FakeGitOps (determined by parametrization)
        repo: Path to the repository root
        worktrees: List of worktree paths (wt1, wt2, etc.)
    """

    git_ops: GitOps
    repo: Path
    worktrees: list[Path]


class GitOpsWithDetached(NamedTuple):
    """Result of git operations setup with detached HEAD worktree.

    Attributes:
        git_ops: Either RealGitOps or FakeGitOps (determined by parametrization)
        repo: Path to the repository root
        detached_wt: Path to the detached HEAD worktree
    """

    git_ops: GitOps
    repo: Path
    detached_wt: Path


class GitOpsWithExistingBranch(NamedTuple):
    """Result of git operations setup with existing branch.

    Attributes:
        git_ops: Either RealGitOps or FakeGitOps (determined by parametrization)
        repo: Path to the repository root
        wt_path: Path to a worktree location (not yet created, for testing add_worktree)
    """

    git_ops: GitOps
    repo: Path
    wt_path: Path


def init_git_repo(repo_path: Path, default_branch: str = "main") -> None:
    """Initialize a git repository with initial commit."""
    subprocess.run(["git", "init", "-b", default_branch], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)

    # Create initial commit
    test_file = repo_path / "README.md"
    test_file.write_text("# Test Repository\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True)


@pytest.fixture(params=["real", "fake"])
def git_ops_impl(request: pytest.FixtureRequest) -> str:
    """Parametrize between 'real' and 'fake' git operations implementations."""
    return request.param


@pytest.fixture
def git_ops(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    git_ops_impl: Literal["real", "fake"],
) -> Iterator[GitOpsSetup]:
    """Provide a git operations implementation (Real or Fake) with setup repo.

    Returns a GitOpsSetup namedtuple with (git_ops, repo) where repo is the path
    to a real git repository that can be used for testing.

    For 'real' implementation: Uses actual git subprocess calls on tmp_path repo
    For 'fake' implementation: Returns FakeGitOps configured with the repo state
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    if git_ops_impl == "real":
        yield GitOpsSetup(git_ops=RealGitOps(), repo=repo)
    else:
        # Fake implementation: configure with repo state
        git_ops = FakeGitOps(
            git_common_dirs={repo: repo / ".git"},
            worktrees={repo: [WorktreeInfo(path=repo, branch="main", is_root=True)]},
            current_branches={repo: "main"},
            default_branches={repo: "main"},
        )
        yield GitOpsSetup(git_ops=git_ops, repo=repo)


@pytest.fixture
def git_ops_with_worktrees(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    git_ops_impl: Literal["real", "fake"],
) -> Iterator[GitOpsWithWorktrees]:
    """Provide git operations with multiple pre-configured worktrees.

    Returns a GitOpsWithWorktrees namedtuple with (git_ops, repo, worktrees)
    where worktrees is a list of worktree paths created via 'git worktree add'.

    For 'real': Creates actual worktrees via git
    For 'fake': Configures FakeGitOps with the worktree state
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    wt1 = tmp_path / "wt1"
    wt2 = tmp_path / "wt2"

    if git_ops_impl == "real":
        # Create real worktrees
        subprocess.run(
            ["git", "worktree", "add", "-b", "feature-1", str(wt1)],
            cwd=repo,
            check=True,
        )
        subprocess.run(
            ["git", "worktree", "add", "-b", "feature-2", str(wt2)],
            cwd=repo,
            check=True,
        )
        yield GitOpsWithWorktrees(git_ops=RealGitOps(), repo=repo, worktrees=[wt1, wt2])
    else:
        # Fake implementation: create directories and configure FakeGitOps
        wt1.mkdir()
        wt2.mkdir()
        git_ops = FakeGitOps(
            git_common_dirs={repo: repo / ".git", wt1: repo / ".git", wt2: repo / ".git"},
            worktrees={
                repo: [
                    WorktreeInfo(path=repo, branch="main", is_root=True),
                    WorktreeInfo(path=wt1, branch="feature-1", is_root=False),
                    WorktreeInfo(path=wt2, branch="feature-2", is_root=False),
                ]
            },
            current_branches={repo: "main", wt1: "feature-1", wt2: "feature-2"},
            default_branches={repo: "main"},
        )
        yield GitOpsWithWorktrees(git_ops=git_ops, repo=repo, worktrees=[wt1, wt2])


@pytest.fixture
def git_ops_with_detached(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    git_ops_impl: Literal["real", "fake"],
) -> Iterator[GitOpsWithDetached]:
    """Provide git operations with a detached HEAD worktree.

    Returns a GitOpsWithDetached namedtuple with (git_ops, repo, detached_wt).
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    wt_detached = tmp_path / "detached"

    if git_ops_impl == "real":
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(wt_detached)],
            cwd=repo,
            check=True,
        )
        yield GitOpsWithDetached(git_ops=RealGitOps(), repo=repo, detached_wt=wt_detached)
    else:
        wt_detached.mkdir()
        git_ops = FakeGitOps(
            git_common_dirs={repo: repo / ".git", wt_detached: repo / ".git"},
            worktrees={
                repo: [
                    WorktreeInfo(path=repo, branch="main", is_root=True),
                    WorktreeInfo(path=wt_detached, branch=None, is_root=False),  # Detached HEAD
                ]
            },
            current_branches={repo: "main", wt_detached: None},
            default_branches={repo: "main"},
        )
        yield GitOpsWithDetached(git_ops=git_ops, repo=repo, detached_wt=wt_detached)


@pytest.fixture
def git_ops_with_existing_branch(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    git_ops_impl: Literal["real", "fake"],
) -> Iterator[GitOpsWithExistingBranch]:
    """Provide git operations with existing branch and worktree path.

    Returns a GitOpsWithExistingBranch namedtuple with (git_ops, repo, wt_path).
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    wt = tmp_path / "wt"

    if git_ops_impl == "real":
        yield GitOpsWithExistingBranch(git_ops=RealGitOps(), repo=repo, wt_path=wt)
    else:
        # For fake, configure FakeGitOps
        git_ops = FakeGitOps(
            git_common_dirs={repo: repo / ".git"},
            worktrees={repo: [WorktreeInfo(path=repo, branch="main", is_root=True)]},
            current_branches={repo: "main"},
            default_branches={repo: "main"},
        )
        yield GitOpsWithExistingBranch(git_ops=git_ops, repo=repo, wt_path=wt)
