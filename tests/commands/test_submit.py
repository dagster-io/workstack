"""Tests for erk submit command."""

from pathlib import Path

from click.testing import CliRunner
from erk_shared.impl_folder import create_impl_folder

from erk.cli.commands.submit import submit_cmd
from erk.core.git.fake import FakeGit
from erk.core.github.fake import FakeGitHub
from erk.core.repo_discovery import RepoContext
from tests.fakes.context import create_test_context


def test_submit_errors_without_plan_folder(tmp_path: Path) -> None:
    """Test submit shows error when no .impl/ folder exists."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    fake_git = FakeGit(current_branches={repo_root: "feature-branch"})
    fake_github = FakeGitHub()
    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(cwd=repo_root, git=fake_git, github=fake_github, repo=repo)

    runner = CliRunner()
    result = runner.invoke(submit_cmd, [], obj=ctx)

    assert result.exit_code == 1
    assert "No .impl/ folder found" in result.output


def test_submit_dry_run_shows_operations(tmp_path: Path) -> None:
    """Test dry-run shows what would happen."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create .impl/ folder
    plan_content = "# Test Plan\n\n1. Step one"
    create_impl_folder(repo_root, plan_content)

    fake_git = FakeGit(current_branches={repo_root: "feature-branch"})
    fake_github = FakeGitHub()
    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(cwd=repo_root, git=fake_git, github=fake_github, repo=repo)

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["--dry-run"], obj=ctx)

    assert result.exit_code == 0
    assert "Would copy .impl/ to .worker-impl/" in result.output
    assert "Would commit and push .worker-impl/" in result.output
    # No longer triggers workflow manually - it auto-triggers on push


def test_submit_errors_with_existing_submission(tmp_path: Path) -> None:
    """Test submit errors when .worker-impl/ already exists."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create both .impl/ and .worker-impl/
    plan_content = "# Test Plan\n\n1. Step one"
    create_impl_folder(repo_root, plan_content)
    (repo_root / ".worker-impl").mkdir()

    fake_git = FakeGit(current_branches={repo_root: "feature-branch"})
    fake_github = FakeGitHub()
    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(cwd=repo_root, git=fake_git, github=fake_github, repo=repo)

    runner = CliRunner()
    result = runner.invoke(submit_cmd, [], obj=ctx)

    assert result.exit_code == 1
    assert ".worker-impl/ folder already exists" in result.output


def test_submit_errors_on_detached_head(tmp_path: Path) -> None:
    """Test submit errors when in detached HEAD state."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create .impl/ folder
    plan_content = "# Test Plan\n\n1. Step one"
    create_impl_folder(repo_root, plan_content)

    # No current branch (detached HEAD)
    fake_git = FakeGit(current_branches={repo_root: None})
    fake_github = FakeGitHub()
    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(cwd=repo_root, git=fake_git, github=fake_github, repo=repo)

    runner = CliRunner()
    result = runner.invoke(submit_cmd, [], obj=ctx)

    assert result.exit_code == 1
    assert "Not on a branch" in result.output
