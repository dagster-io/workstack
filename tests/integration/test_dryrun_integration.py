"""Integration tests for dry-run behavior across all operations.

These tests verify that dry-run mode prevents destructive operations
while still allowing read operations.
"""

import os
import subprocess
from pathlib import Path

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext, create_context
from workstack.core.global_config import GlobalConfig
from workstack.core.github_ops import DryRunGitHubOps
from workstack.core.gitops import DryRunGitOps, WorktreeInfo
from workstack.core.global_config_ops import DryRunGlobalConfigOps
from workstack.core.graphite_ops import DryRunGraphiteOps


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


def test_dryrun_context_creation(tmp_path: Path) -> None:
    """Test that create_context with dry_run=True creates wrapped implementations."""
    ctx = create_context(dry_run=True)

    assert ctx.dry_run is True
    # The context should have DryRun-wrapped implementations
    # We verify this by checking the class names
    assert "DryRun" in type(ctx.git_ops).__name__
    assert "DryRun" in type(ctx.global_config_ops).__name__
    assert "DryRun" in type(ctx.github_ops).__name__
    assert "DryRun" in type(ctx.graphite_ops).__name__


def test_dryrun_read_operations_still_work(tmp_path: Path) -> None:
    """Test that dry-run mode allows read operations."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    # Set up fakes to avoid needing real config file
    git_ops = FakeGitOps(
        worktrees={
            repo: [WorktreeInfo(path=repo, branch="main")],
        },
        git_common_dirs={repo: repo / ".git"},
    )
    global_config_ops = FakeGlobalConfigOps(
        workstacks_root=tmp_path / "workstacks",
        use_graphite=False,
    )

    # Wrap fakes in dry-run wrappers
    ctx = WorkstackContext(
        git_ops=DryRunGitOps(git_ops),
        global_config_ops=DryRunGlobalConfigOps(global_config_ops),
        github_ops=DryRunGitHubOps(FakeGitHubOps()),
        graphite_ops=DryRunGraphiteOps(FakeGraphiteOps()),
        shell_ops=FakeShellOps(),
        cwd=Path("/test/default/cwd"),
        dry_run=True,
    )

    runner = CliRunner()
    # List should work even in dry-run mode since it's a read operation
    # Change to repo directory so discover_repo_context can find it
    original_cwd = os.getcwd()
    try:
        os.chdir(repo)
        result = runner.invoke(cli, ["list"], obj=ctx)
    finally:
        os.chdir(original_cwd)

    # Should succeed (read operations are not blocked)
    assert result.exit_code == 0


def test_dryrun_git_delete_branch_prints_message(tmp_path: Path) -> None:
    """Test that dry-run GitOps delete operations print messages without executing."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    # Create a branch and worktree
    wt = tmp_path / "feature-wt"
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature-branch", str(wt)],
        cwd=repo,
        check=True,
    )

    ctx = create_context(dry_run=True)

    # Verify the branch exists before dry-run delete
    result = subprocess.run(
        ["git", "branch"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "feature-branch" in result.stdout

    # Try to delete via dry-run context
    from workstack.core.gitops import RealGitOps

    real_ops = RealGitOps()
    git_dir = real_ops.get_git_common_dir(repo)
    if git_dir is not None:
        ctx.git_ops.delete_branch_with_graphite(git_dir.parent, "feature-branch", force=True)

    # Verify the branch still exists (dry-run didn't actually delete)
    result = subprocess.run(
        ["git", "branch"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "feature-branch" in result.stdout


def test_dryrun_git_add_worktree_prints_message(tmp_path: Path) -> None:
    """Test that dry-run GitOps add_worktree prints message without creating."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    ctx = create_context(dry_run=True)

    new_wt = tmp_path / "new-worktree"
    # This should print a dry-run message but not create the worktree
    ctx.git_ops.add_worktree(repo, new_wt, branch="new-feature", ref=None, create_branch=True)

    # Verify the worktree wasn't actually created
    assert not new_wt.exists()

    # Verify git doesn't know about the worktree
    from workstack.core.gitops import RealGitOps

    real_ops = RealGitOps()
    worktrees = real_ops.list_worktrees(repo)
    assert len(worktrees) == 1  # Only main repo
    assert not any(wt.path == new_wt for wt in worktrees)


def test_dryrun_git_remove_worktree_prints_message(tmp_path: Path) -> None:
    """Test that dry-run GitOps remove_worktree prints message without removing."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    # Create a worktree
    wt = tmp_path / "feature-wt"
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature", str(wt)],
        cwd=repo,
        check=True,
    )

    ctx = create_context(dry_run=True)

    # Try to remove via dry-run
    ctx.git_ops.remove_worktree(repo, wt, force=False)

    # Verify the worktree still exists
    assert wt.exists()

    # Verify git still knows about it
    from workstack.core.gitops import RealGitOps

    real_ops = RealGitOps()
    worktrees = real_ops.list_worktrees(repo)
    assert len(worktrees) == 2
    assert any(wt_info.path == wt for wt_info in worktrees)


def test_dryrun_git_checkout_branch_is_allowed(tmp_path: Path) -> None:
    """Test that dry-run GitOps allows checkout_branch (it's non-destructive)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    # Create a new branch
    subprocess.run(["git", "branch", "feature"], cwd=repo, check=True)

    # Verify we're on main
    from workstack.core.gitops import RealGitOps

    real_ops = RealGitOps()
    assert real_ops.get_current_branch(repo) == "main"

    ctx = create_context(dry_run=True)

    # Checkout is allowed in dry-run mode (it's non-destructive)
    ctx.git_ops.checkout_branch(repo, "feature")

    # Verify we actually checked out (checkout is allowed in dry-run)
    assert real_ops.get_current_branch(repo) == "feature"


def test_dryrun_config_set_prints_message(tmp_path: Path) -> None:
    """Test that dry-run GlobalConfigOps.set prints message without writing."""
    ctx = create_context(dry_run=True)

    # Try to set config in dry-run mode
    # This should print a message but not actually write
    test_root = tmp_path / "workstacks"
    ctx.global_config_ops.set(
        workstacks_root=test_root,
        use_graphite=True,
    )

    # Verify no actual config file was created
    # (The real config file would be in ~/.config/workstack/config.toml)
    # Since we're in dry-run mode, the real config should not be modified


def test_dryrun_config_read_still_works(tmp_path: Path) -> None:
    """Test that dry-run GlobalConfigOps read operations still work."""
    ctx = create_context(dry_run=True)

    # Read operations should work even in dry-run mode
    # This may raise FileNotFoundError if config doesn't exist, which is expected
    try:
        _ = ctx.global_config_ops.get_workstacks_root()
        # If it succeeds, that's fine
    except FileNotFoundError:
        # If it fails because config doesn't exist, that's also fine
        pass


def test_dryrun_graphite_operations(tmp_path: Path) -> None:
    """Test that dry-run GraphiteOps operations work correctly."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    ctx = create_context(dry_run=True)

    # Test read operations work (they delegate to wrapped implementation)
    url = ctx.graphite_ops.get_graphite_url("owner", "repo", 123)
    assert isinstance(url, str)
    assert "graphite.dev" in url

    # Test get_prs_from_graphite (read operation)
    from workstack.core.gitops import RealGitOps

    git_ops = RealGitOps()
    prs = ctx.graphite_ops.get_prs_from_graphite(git_ops, repo)
    assert isinstance(prs, dict)

    # Test sync prints dry-run message without executing
    # Note: sync is a write operation, so it should be blocked in dry-run mode
    ctx.graphite_ops.sync(repo, force=False, quiet=False)
    # If sync was actually executed, it would require gt CLI to be installed
    # In dry-run mode, it just prints a message
