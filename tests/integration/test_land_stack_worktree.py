"""Integration test for land-stack command with linked worktrees.

This test uses real git operations to verify land-stack behavior when run
from a linked worktree where the current branch is being landed.
"""

import os
import subprocess
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext
from erk.core.git.real import RealGit
from erk.core.github.fake import FakeGitHub
from erk.core.graphite.fake import FakeGraphite
from tests.fakes.shell import FakeShell
from tests.test_utils.builders import BranchStackBuilder


def test_land_stack_from_linked_worktree_on_current_branch(tmp_path: Path) -> None:
    """Test land-stack succeeds when run from current worktree on branch being landed.

    After validation changes, land-stack EXCLUDES the current branch in the current
    worktree from conflict detection, only flagging branches in OTHER worktrees.

    Expected behavior: Command should succeed without worktree conflict errors.

    This test uses:
    - Real git repo and worktrees (to test actual worktree detection)
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
    repo_dir = tmp_path / "erks" / "repo"
    repo_dir.mkdir(parents=True)
    worktree_path = repo_dir / "feat-1-work"

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
        git_ops = RealGit()

        graphite_ops = FakeGraphite(
            branches=BranchStackBuilder().add_linear_stack("feat-1").build(),
            stacks={
                "feat-1": ["main", "feat-1"],
            },
        )

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Add feature 1"),
            },
            pr_bases={
                100: "main",
            },
        )

        global_config_ops = GlobalConfig(
            erk_root=repo_dir.parent,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            cwd=worktree_path,
            dry_run=True,  # Match --dry-run flag on line 164
        )

        runner = CliRunner()

        # Try to land feat-1 from the linked worktree
        # Use --force to skip confirmation, --dry-run to skip subprocess calls
        result = runner.invoke(cli, ["land-stack", "--force", "--dry-run"], obj=test_ctx)

        # Should succeed - current branch in current worktree is not a conflict
        assert result.exit_code == 0, f"Expected success but got: {result.output}"
        assert (
            "Cannot land stack - branches are checked out in multiple worktrees"
            not in result.output
        )

    finally:
        # Restore original directory
        os.chdir(original_cwd)


def test_land_stack_with_trunk_in_worktree(tmp_path: Path) -> None:
    """Test land-stack succeeds when run from current worktree on branch being landed.

    After validation changes, land-stack EXCLUDES the current branch in the current
    worktree from conflict detection, only flagging branches in OTHER worktrees.

    Expected behavior: Command should succeed without worktree conflict errors.

    This test uses:
    - Real git repo and worktrees (to test actual worktree detection)
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
    repo_dir = tmp_path / "erks" / "repo"
    repo_dir.mkdir(parents=True)
    main_worktree = repo_dir / "main-work"

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
        git_ops = RealGit()

        graphite_ops = FakeGraphite(
            branches=BranchStackBuilder().add_linear_stack("feat-1").build(),
            stacks={
                "feat-1": ["main", "feat-1"],
            },
        )

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Add feature 1"),
            },
            pr_bases={
                100: "main",
            },
        )

        global_config_ops = GlobalConfig(
            erk_root=repo_dir.parent,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            cwd=repo,
            dry_run=True,  # Use dry-run to skip actual PR merge
        )

        runner = CliRunner()

        # Land feat-1 stack (this will trigger validation)
        result = runner.invoke(cli, ["land-stack", "--force", "--dry-run"], obj=test_ctx)

        # Should succeed - current branch in current worktree is not a conflict
        assert result.exit_code == 0, f"Expected success but got: {result.output}"
        assert (
            "Cannot land stack - branches are checked out in multiple worktrees"
            not in result.output
        )

    finally:
        # Restore original directory
        os.chdir(original_cwd)


def test_land_stack_leaves_root_on_trunk(tmp_path: Path) -> None:
    """Regression test: root worktree should stay on trunk, not checkout feature branch.

    This is a critical bug fix: during land-stack operation, the root worktree should
    remain on trunk (main/master). The buggy code would checkout the feature branch at
    root during the sync trunk phase, causing "branch checked out in multiple worktrees"
    errors on subsequent lands.

    Bug context:
    - On 2025-11-20, session-log-preprocessing-kit-25-11-20 was incorrectly checked out
      at /Users/schrockn/code/erk (root worktree) during land-stack
    - This blocked subsequent lands because git doesn't allow same branch in multiple worktrees
    - Root cause: lines 183-186 in execution.py tried to "restore" feature branch at root

    This test uses:
    - Real git repo and worktrees (to verify actual git state)
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

    # CRITICAL: Switch root worktree back to main before creating linked worktree
    # This mimics the real-world scenario where root stays on trunk
    subprocess.run(
        ["git", "checkout", "main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create linked worktree for feat-1
    repo_dir = tmp_path / "erks" / "repo"
    repo_dir.mkdir(parents=True)
    worktree_path = repo_dir / "feat-1-work"

    subprocess.run(
        ["git", "worktree", "add", str(worktree_path), "feat-1"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Run land-stack from the linked worktree
    original_cwd = Path.cwd()
    os.chdir(worktree_path)

    try:
        # Set up test context with real git ops + fake others
        git_ops = RealGit()

        graphite_ops = FakeGraphite(
            branches=BranchStackBuilder().add_linear_stack("feat-1").build(),
            stacks={
                "feat-1": ["main", "feat-1"],
            },
        )

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Add feature 1"),
            },
            pr_bases={
                100: "main",
            },
        )

        global_config_ops = GlobalConfig(
            erk_root=repo_dir.parent,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            cwd=worktree_path,
            dry_run=True,  # Use dry-run to skip actual PR merge
        )

        runner = CliRunner()

        # Land feat-1 from the linked worktree
        result = runner.invoke(cli, ["land-stack", "--force", "--dry-run"], obj=test_ctx)

        # Should succeed
        assert result.exit_code == 0, f"Expected success but got: {result.output}"

        # CRITICAL ASSERTION: Verify root worktree is still on main, not feat-1
        # This is the key bug fix validation
        current_branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        root_branch = current_branch_result.stdout.strip()

        assert root_branch == "main", (
            f"BUG: Root worktree is on '{root_branch}', expected 'main'. "
            f"The sync trunk phase incorrectly checked out the feature branch at root. "
            f"This causes 'branch checked out in multiple worktrees' errors."
        )

    finally:
        # Restore original directory
        os.chdir(original_cwd)
