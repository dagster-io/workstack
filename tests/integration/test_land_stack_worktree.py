"""Integration test for land-stack command with linked worktrees.

This test uses real git operations to verify land-stack behavior when run
from a linked worktree where the current branch is being landed.
"""

import os
import subprocess
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.branch_metadata import BranchMetadata
from erk.core.context import ErkContext
from erk.core.gitops import RealGitOps
from erk.core.global_config import GlobalConfig
from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps


def test_land_stack_from_linked_worktree_on_current_branch(tmp_path: Path) -> None:
    """Test land-stack when run from linked worktree on branch being landed.

    Bug: When running land-stack from a linked worktree where the current branch
    is part of the stack being landed, the command tries to checkout the branch
    in the repo root, which fails because git won't allow checking out a branch
    that's already checked out in a linked worktree.

    Expected behavior after fix: Should skip checkout when already on the branch.

    This test uses:
    - Real git repo and worktrees (to trigger actual git checkout error)
    - Fake Graphite/GitHub ops (to avoid external dependencies)
    """
    # Create real git repository
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create initial commit on main
    readme = repo / "README.md"
    readme.write_text("# Test Repository\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create feature branch
    subprocess.run(
        ["git", "checkout", "-b", "feat-1"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    feature_file = repo / "feature.txt"
    feature_file.write_text("Add feature 1\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "feature.txt"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add feature 1"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Switch back to main so feat-1 isn't checked out in root
    subprocess.run(
        ["git", "checkout", "main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create linked worktree for feat-1
    workstacks_dir = tmp_path / "workstacks" / "repo"
    workstacks_dir.mkdir(parents=True)
    worktree_path = workstacks_dir / "feat-1-work"

    subprocess.run(
        ["git", "worktree", "add", str(worktree_path), "feat-1"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Change to linked worktree (this is where user would be)
    original_cwd = Path.cwd()
    os.chdir(worktree_path)

    try:
        # Set up test context with real git ops + fake others
        git_ops = RealGitOps()

        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            stacks={
                "feat-1": ["main", "feat-1"],
            },
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Add feature 1"),
            },
            pr_bases={
                100: "main",
            },
        )

        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_dir.parent,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        test_ctx = ErkContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=worktree_path,
            dry_run=True,  # Match --dry-run flag on line 164
        )

        runner = CliRunner()

        # Try to land feat-1 from the linked worktree
        # Use --force to skip confirmation, --dry-run to skip subprocess calls
        result = runner.invoke(cli, ["land-stack", "--force", "--dry-run"], obj=test_ctx)

        # After fix: Command should succeed when run from linked worktree
        # The fix detects we're already on the branch and skips checkout
        # (dry-run mode validates flow works without executing real operations)
        assert result.exit_code == 0
        assert "Landing 1 PR" in result.output
        assert "feat-1" in result.output

    finally:
        # Restore original directory
        os.chdir(original_cwd)


def test_land_stack_with_trunk_in_worktree(tmp_path: Path) -> None:
    """Test land-stack trunk sync when trunk is checked out in a worktree.

    Bug: When trunk is checked out in a worktree, _execute_sync_trunk_phase()
    pulls at repo_root instead of the worktree location, leaving trunk stale.
    This causes gt sync -f to fail with "commits are not in main" error.

    Expected behavior after fix: Should detect trunk is in worktree and pull there.

    This test uses:
    - Real git repo and worktrees (to test actual worktree path detection)
    - Fake Graphite/GitHub ops (to avoid external dependencies)
    """
    # Create real git repository
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create initial commit on main
    readme = repo / "README.md"
    readme.write_text("# Test Repository\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create feature branch
    subprocess.run(
        ["git", "checkout", "-b", "feat-1"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    feature_file = repo / "feature.txt"
    feature_file.write_text("Add feature 1\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "feature.txt"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add feature 1"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create linked worktree for main (this is the key setup for the bug)
    workstacks_dir = tmp_path / "workstacks" / "repo"
    workstacks_dir.mkdir(parents=True)
    main_worktree = workstacks_dir / "main-work"

    subprocess.run(
        ["git", "worktree", "add", str(main_worktree), "main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Stay in repo root (where feat-1 is checked out)
    # This simulates the user running land-stack from a feature branch
    # while main is checked out in a worktree
    original_cwd = Path.cwd()

    try:
        # Set up test context with real git ops + fake others
        git_ops = RealGitOps()

        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            stacks={
                "feat-1": ["main", "feat-1"],
            },
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Add feature 1"),
            },
            pr_bases={
                100: "main",
            },
        )

        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_dir.parent,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        test_ctx = ErkContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=repo,
            dry_run=True,  # Use dry-run to skip actual PR merge
        )

        runner = CliRunner()

        # Land feat-1 stack (this will trigger trunk sync phase)
        # The fix should detect main is in a worktree and pull there
        result = runner.invoke(cli, ["land-stack", "--force", "--dry-run"], obj=test_ctx)

        # After fix: Command should succeed
        # The trunk sync phase should detect main is in main_worktree and pull there
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Landing 1 PR" in result.output
        assert "feat-1" in result.output

        # Verify that main worktree location is detected correctly
        # (by checking that git operations don't fail with "already checked out" error)
        assert "already checked out" not in result.output.lower()
        assert "fatal" not in result.output.lower()

    finally:
        # Restore original directory
        os.chdir(original_cwd)
