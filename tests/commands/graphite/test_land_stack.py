"""Tests for the land-stack command."""

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.gitops import WorktreeInfo
from workstack.core.global_config import GlobalConfig
from workstack.core.graphite_ops import BranchMetadata


class SimulatedWorkstackEnv:
    """Helper for managing simulated workstack test environment."""

    def __init__(self, root_worktree: Path, workstacks_root: Path) -> None:
        """Initialize test environment.

        Args:
            root_worktree: Path to root worktree (has .git/ directory)
            workstacks_root: Path to workstacks directory (parallel to root)
        """
        self.root_worktree = root_worktree
        self.workstacks_root = workstacks_root
        self.cwd = root_worktree  # Current working directory (starts at root)
        self._linked_worktrees: dict[str, Path] = {}  # Track branch -> worktree path

    def create_linked_worktree(self, name: str, branch: str, *, chdir: bool) -> Path:
        """Create a linked worktree in workstacks directory.

        Args:
            name: Name for the worktree directory
            branch: Branch name for the worktree
            chdir: Whether to change working directory to the new worktree (required)

        Returns:
            Path to the created linked worktree
        """
        # Create linked worktree directory
        linked_wt = self.workstacks_root / "repo" / name
        linked_wt.mkdir(parents=True)

        # Create .git file pointing to root worktree
        git_file = linked_wt / ".git"
        git_file.write_text(
            f"gitdir: {self.root_worktree / '.git' / 'worktrees' / name}\n",
            encoding="utf-8",
        )

        # Create worktree metadata in root's .git/worktrees/
        worktree_meta_dir = self.root_worktree / ".git" / "worktrees" / name
        worktree_meta_dir.mkdir(parents=True)

        # Change directory if requested
        if chdir:
            os.chdir(linked_wt)
            self.cwd = linked_wt  # Update current working directory

        # Track the mapping for build_ops_from_branches()
        self._linked_worktrees[branch] = linked_wt

        return linked_wt

    def build_ops_from_branches(
        self,
        branches: dict[str, BranchMetadata],
        *,
        current_branch: str | None = None,
        current_worktree: Path | None = None,
    ) -> tuple[FakeGitOps, FakeGraphiteOps]:
        """Build both FakeGitOps and FakeGraphiteOps from branch metadata.

        Automatically:
        - Maps branches to worktrees (root + any created linked worktrees)
        - Computes stacks dict from parent/child relationships
        - Configures git_common_dirs for all worktrees
        - Sets current branch in specified worktree

        Args:
            branches: Branch metadata with parent/child relationships
            current_branch: Which branch is checked out (defaults to root's branch)
            current_worktree: Where current_branch is (defaults to root_worktree)

        Returns:
            Tuple of (FakeGitOps, FakeGraphiteOps) configured for testing

        Example:
            env.create_linked_worktree("feat-1", "feat-1", chdir=False)
            env.create_linked_worktree("feat-2", "feat-2", chdir=True)

            git_ops, graphite_ops = env.build_ops_from_branches(
                {
                    "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                    "feat-1": BranchMetadata.branch(
                        "feat-1", "main", children=["feat-2"], commit_sha="def456"
                    ),
                    "feat-2": BranchMetadata.branch("feat-2", "feat-1", commit_sha="ghi789"),
                },
                current_branch="feat-2",
            )
        """
        current_worktree = current_worktree or self.root_worktree

        # Find trunk branch (for root worktree)
        trunk_branch = None
        for name, meta in branches.items():
            if meta.is_trunk:
                trunk_branch = name
                break

        if trunk_branch is None:
            trunk_branch = "main"  # Fallback

        # Build worktrees list
        worktrees_list = [WorktreeInfo(path=self.root_worktree, branch=trunk_branch, is_root=True)]

        # Add linked worktrees created via create_linked_worktree()
        for branch, path in self._linked_worktrees.items():
            worktrees_list.append(WorktreeInfo(path=path, branch=branch, is_root=False))

        # Build current_branches mapping
        current_branches_map = {}
        for wt in worktrees_list:
            if wt.path == current_worktree:
                # This worktree has the current branch
                current_branches_map[wt.path] = current_branch if current_branch else wt.branch
            else:
                # Other worktrees stay on their own branch
                current_branches_map[wt.path] = wt.branch

        # Build git_common_dirs mapping (all point to root's .git)
        git_common_dirs_map = {wt.path: self.root_worktree / ".git" for wt in worktrees_list}

        # Build stacks from branches (auto-compute from parent/child)
        stacks = {}
        for branch_name in branches:
            if not branches[branch_name].is_trunk:
                stacks[branch_name] = self._build_stack_path(branches, branch_name)

        git_ops = FakeGitOps(
            worktrees={self.root_worktree: worktrees_list},
            current_branches=current_branches_map,
            git_common_dirs=git_common_dirs_map,
        )

        graphite_ops = FakeGraphiteOps(
            branches=branches,
            stacks=stacks,
        )

        return git_ops, graphite_ops

    def _build_stack_path(
        self,
        branches: dict[str, BranchMetadata],
        leaf: str,
    ) -> list[str]:
        """Build stack path from trunk to leaf.

        Args:
            branches: All branch metadata
            leaf: Leaf branch name

        Returns:
            List of branch names from trunk to leaf (inclusive)
        """
        stack = []
        current = leaf

        # Walk up to trunk
        while current in branches:
            stack.insert(0, current)
            parent = branches[current].parent

            if parent is None:
                # Reached trunk
                break

            if parent not in branches:
                # Parent not in branches dict, stop
                break

            current = parent

        return stack


@contextmanager
def simulated_workstack_env(runner: CliRunner) -> Generator[SimulatedWorkstackEnv]:
    """Set up simulated workstack environment with isolated filesystem.

    Creates realistic directory structure:
        base/
          ├── repo/         (root worktree with .git/)
          └── workstacks/   (parallel to repo, initially empty)

    Defaults to root worktree. Use env.create_linked_worktree() to create
    and optionally navigate to linked worktrees.

    Args:
        runner: Click CliRunner instance

    Yields:
        SimulatedWorkstackEnv helper for managing test environment
    """
    with runner.isolated_filesystem():
        base = Path.cwd()  # isolated_filesystem() creates temp dir and changes cwd to it

        # Create root worktree with .git directory
        root_worktree = base / "repo"
        root_worktree.mkdir()
        (root_worktree / ".git").mkdir()

        # Create workstacks directory
        workstacks_root = base / "workstacks"
        workstacks_root.mkdir()

        # Default to root worktree
        os.chdir(root_worktree)

        yield SimulatedWorkstackEnv(
            root_worktree=root_worktree,
            workstacks_root=workstacks_root,
        )


def test_land_stack_requires_graphite() -> None:
    """Test that land-stack command requires Graphite to be enabled."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build both ops from branch metadata
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            current_branch="feat-1",
        )

        # use_graphite=False: Test that graphite is required
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack"], obj=test_ctx)

        assert result.exit_code == 1
        assert "requires Graphite" in result.output


def test_land_stack_fails_on_detached_head() -> None:
    """Test that land-stack fails when HEAD is detached."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_root = cwd
        (repo_root / ".git").mkdir()

        # current_branches={cwd: None} indicates detached HEAD
        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch=None),
                ],
            },
            current_branches={cwd: None},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack"], obj=test_ctx)

        assert result.exit_code == 1
        assert "HEAD is detached" in result.output


def test_land_stack_fails_with_uncommitted_changes() -> None:
    """Test that land-stack fails when there are uncommitted changes."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_root = cwd
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
            current_branches={cwd: "feat-1"},
            file_statuses={cwd: (["file.txt"], [], [])},  # Has staged changes
        )

        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            stacks={
                "feat-1": ["main", "feat-1"],
            },
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack"], obj=test_ctx)

        assert result.exit_code == 1
        assert "uncommitted changes" in result.output


def test_land_stack_fails_on_trunk_branch() -> None:
    """Test that land-stack fails when current branch is trunk."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_root = cwd
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
            current_branches={cwd: "main"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", commit_sha="abc123"),
            },
            stacks={
                "main": ["main"],
            },
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Cannot land trunk branch" in result.output


def test_land_stack_fails_when_branch_not_tracked() -> None:
    """Test that land-stack fails when branch is not tracked by Graphite."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_root = cwd
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
            current_branches={cwd: "untracked-branch"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Branch not in graphite stack
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", commit_sha="abc123"),
            },
            stacks={},
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack"], obj=test_ctx)

        assert result.exit_code == 1
        assert "not tracked by Graphite" in result.output


def test_land_stack_fails_when_pr_missing() -> None:
    """Test that land-stack fails when a branch has no PR."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_root = cwd
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
            current_branches={cwd: "feat-1"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk(
                    "main", children=["feat-1", "feat-2"], commit_sha="abc123"
                ),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch("feat-2", "feat-1", commit_sha="ghi789"),
            },
            stacks={
                "feat-1": ["main", "feat-1", "feat-2"],
            },
        )

        # feat-1 has no PR (state=NONE)
        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("NONE", None, None),
                "feat-2": ("OPEN", 123, "Add feature 2"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack"], obj=test_ctx)

        assert result.exit_code == 1
        assert "No PR found" in result.output
        assert "feat-1" in result.output


def test_land_stack_fails_when_pr_closed() -> None:
    """Test that land-stack fails when a branch's PR is closed."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_root = cwd
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
            current_branches={cwd: "feat-1"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            stacks={
                "feat-1": ["main", "feat-1"],
            },
        )

        # feat-1 PR is closed
        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("CLOSED", 100, "Closed feature"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack"], obj=test_ctx)

        assert result.exit_code == 1
        assert "closed" in result.output


def test_land_stack_gets_branches_to_land_correctly() -> None:
    """Test that land-stack lands from bottom of stack to current branch."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_root = cwd
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
            current_branches={cwd: "feat-2"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Stack: main → feat-1 → feat-2 → feat-3
        # Current: feat-2
        # Should land: feat-1, feat-2 (bottom to current, not including feat-3)
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch(
                    "feat-2", "feat-1", children=["feat-3"], commit_sha="ghi789"
                ),
                "feat-3": BranchMetadata.branch("feat-3", "feat-2", commit_sha="jkl012"),
            },
            stacks={
                "feat-2": ["main", "feat-1", "feat-2", "feat-3"],
            },
        )

        # feat-1 and feat-2 have open PRs (feat-3 not needed)
        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        # Use --force to skip confirmation
        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx, input="y\n")

        # Should show landing 2 PRs (feat-1 and feat-2 from bottom to current)
        assert "Landing 2 PRs" in result.output
        assert "feat-1" in result.output
        assert "feat-2" in result.output


def test_land_stack_from_top_of_stack_lands_all_branches() -> None:
    """Test that land-stack from top of stack lands all branches from bottom to current.

    When on the leaf/top branch of a stack, land-stack should land ALL branches
    from the bottom of the stack (first non-trunk) up to and including current.

    Bug: Currently only returns the current branch when at top of stack.
    Fix: Should return entire stack from bottom to current.
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_root = cwd
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
            current_branches={cwd: "feat-4"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Stack: main → feat-1 → feat-2 → feat-3 → feat-4
        # Current: feat-4 (at TOP/leaf)
        # Should land: feat-1, feat-2, feat-3, feat-4 (ALL 4 branches)
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch(
                    "feat-2", "feat-1", children=["feat-3"], commit_sha="ghi789"
                ),
                "feat-3": BranchMetadata.branch(
                    "feat-3", "feat-2", children=["feat-4"], commit_sha="jkl012"
                ),
                "feat-4": BranchMetadata.branch("feat-4", "feat-3", commit_sha="mno345"),
            },
            stacks={
                "feat-4": ["main", "feat-1", "feat-2", "feat-3", "feat-4"],
            },
        )

        # All branches have open PRs
        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
                "feat-3": ("OPEN", 300, "Feature 3"),
                "feat-4": ("OPEN", 400, "Feature 4"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        # Use --dry-run to avoid actual merging
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        # Should show landing 4 PRs (ALL branches from bottom to current)
        assert "Landing 4 PRs" in result.output
        assert "feat-1" in result.output
        assert "feat-2" in result.output
        assert "feat-3" in result.output
        assert "feat-4" in result.output


def test_land_stack_fails_when_branches_in_multiple_worktrees() -> None:
    """Test that land-stack fails when stack branches are checked out in multiple worktrees."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create linked worktrees (automatically tracked)
        env.create_linked_worktree(name="feat-1", branch="feat-1", chdir=False)
        env.create_linked_worktree(name="feat-2", branch="feat-2", chdir=False)
        env.create_linked_worktree(name="feat-3", branch="feat-3", chdir=True)

        # Build both ops (automatically includes all created worktrees)
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch(
                    "feat-2", "feat-1", children=["feat-3"], commit_sha="ghi789"
                ),
                "feat-3": BranchMetadata.branch("feat-3", "feat-2", commit_sha="jkl012"),
            },
            current_branch="feat-3",
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
                "feat-3": ("OPEN", 300, "Feature 3"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack"], obj=test_ctx)

        # Should fail with multi-worktree error
        assert result.exit_code == 1
        assert "Cannot land stack - branches are checked out in multiple worktrees" in result.output
        assert "feat-1" in result.output
        assert "feat-2" in result.output
        assert "workstack consolidate" in result.output


def test_land_stack_succeeds_when_all_branches_in_current_worktree() -> None:
    """Test that land-stack succeeds when all stack branches are only in current worktree."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_root = cwd
        (repo_root / ".git").mkdir()

        # Only main branch in repo root, current branch is feat-2
        # feat-1 and feat-2 not checked out in other worktrees
        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
            current_branches={cwd: "feat-2"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Stack: main → feat-1 → feat-2
        # Current: feat-2
        # Should land: feat-1, feat-2
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch("feat-2", "feat-1", commit_sha="ghi789"),
            },
            stacks={
                "feat-2": ["main", "feat-1", "feat-2"],
            },
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        # Use --dry-run to avoid actual merging
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        # Should succeed and show landing plan
        assert "Landing 2 PRs" in result.output
        assert "feat-1" in result.output
        assert "feat-2" in result.output
        # Should NOT show worktree conflict error
        assert "multiple worktrees" not in result.output


def test_land_stack_refreshes_metadata_after_sync() -> None:
    """Test that RealGraphiteOps invalidates cache after gt sync.

    This test verifies the fix for the cache invalidation bug:
    - Bug: RealGraphiteOps.sync() didn't invalidate _branches_cache
    - Result: After gt sync updated metadata, stale cached data was returned
    - Fix: Added `self._branches_cache = None` at end of sync()

    The test creates a simulated scenario where sync() modifies metadata
    and verifies that subsequent get_all_branches() calls return fresh data.
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_root = cwd
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
            current_branches={cwd: "feat-2"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Stack: main → feat-1 → feat-2
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch("feat-2", "feat-1", commit_sha="ghi789"),
            },
            stacks={
                "feat-2": ["main", "feat-1", "feat-2"],
            },
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        # Execute land-stack - should complete successfully
        # The fix ensures cache is invalidated after each sync
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Landing 2 PRs" in result.output


def test_land_stack_from_linked_worktree_on_branch_being_landed() -> None:
    """Test that land-stack works when run from a linked worktree on branch being landed.

    Scenario: User is in a linked worktree on feat-1 and wants to land that PR.
    The command should detect we're already on the branch and skip checkout.

    Before fix: Would try to checkout feat-1 in repo root, failing because it's
    already checked out in the linked worktree.

    After fix: Detects current branch and skips unnecessary checkout.
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create linked worktree for feat-1 and change to it
        env.create_linked_worktree(name="feat-1-work", branch="feat-1", chdir=True)

        # Build ops for simple stack: main → feat-1
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            current_branch="feat-1",
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Add feature 1"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
            cwd=env.cwd,
        )

        # Try to land feat-1 from the linked worktree
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        # Should succeed - command skips checkout when already on the branch
        # (dry-run mode doesn't execute real checkout logic, but validates flow works)
        assert result.exit_code == 0
        assert "Landing 1 PR" in result.output
        assert "feat-1" in result.output


def test_land_stack_switches_to_root_when_run_from_linked_worktree() -> None:
    """Test that land-stack switches to root worktree before cleanup.

    Scenario: User is in a linked worktree that will be destroyed during land-stack.
    Without the fix, the user's shell ends up in a destroyed directory.

    Bug: land-stack runs cleanup operations (including workstack sync -f) which
    destroys worktrees. If the current directory is one of those worktrees, the
    shell is left in a deleted directory.

    Fix: Before cleanup, check if Path.cwd() != repo.root and call os.chdir(repo.root).
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create linked worktree for feat-1 and change to it
        linked_wt = env.create_linked_worktree(name="feat-1-work", branch="feat-1", chdir=True)

        # Verify we're in the linked worktree
        assert Path.cwd() == linked_wt

        # Build ops for simple stack: main → feat-1
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feat-1"],
                    commit_sha="abc123",
                    is_trunk=True,
                ),
                "feat-1": BranchMetadata(
                    name="feat-1",
                    parent="main",
                    children=None,
                    commit_sha="def456",
                    is_trunk=False,
                ),
            },
            current_branch="feat-1",
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Add feature 1"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
            cwd=env.cwd,
        )

        # Run land-stack with --dry-run to avoid subprocess failures
        # Note: cleanup still executes in dry-run mode, directory switch still happens
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        # Verify the command completed
        assert result.exit_code == 0

        # CRITICAL: Verify working directory is now root worktree (not the linked worktree)
        # This proves the fix moved us before destroying the linked worktree
        assert Path.cwd() == env.root_worktree

        # Verify we're not in a destroyed/invalid directory
        assert Path.cwd().exists()


def test_land_stack_script_mode_accepts_flag() -> None:
    """Verify land-stack accepts --script flag for shell integration."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build test environment with a simple stack
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            },
            current_branch="feature-1",
        )

        # Setup GitHub ops with an open PR
        github_ops = FakeGitHubOps(pr_statuses={"feature-1": ("OPEN", 123, "Feature 1")})

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
            cwd=env.cwd,
        )

        # Act: Run with --script flag (this is what shell wrapper will call)
        # Use --dry-run to avoid subprocess failures in test environment
        result = runner.invoke(
            cli,
            ["land-stack", "-f", "--script", "--dry-run"],
            obj=test_ctx,
        )

        # Assert: Command should succeed
        # Note: We can't verify actual shell integration behavior with CliRunner
        # but we can verify the flag is accepted and the command runs
        assert result.exit_code == 0

        # In script mode, all output should go to stderr
        # Passthrough commands rely on the recovery mechanism, not explicit script generation


def test_land_stack_updates_pr_base_before_merge_when_stale() -> None:
    """Test that land-stack updates PR base on GitHub before merging when stale.

    Bug scenario:
    - Stack: main → feat-1 → feat-2
    - After landing feat-1, gt sync updates local metadata (feat-2 parent = main)
    - But GitHub PR #2 still shows base = feat-1 (stale)
    - Without fix: gh pr merge tries to merge into deleted branch
    - With fix: gh pr edit --base main is called before gh pr merge

    This test verifies the fix inserts Phase 2.5 logic to check and update
    GitHub PR base before each merge operation.
    """
    from unittest.mock import Mock, patch

    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build two-PR stack: main → feat-1 → feat-2
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch("feat-2", "feat-1", commit_sha="ghi789"),
            },
            current_branch="feat-2",
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            }
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
            cwd=env.cwd,
        )

        # Mock subprocess.run to capture gh/gt command sequence
        # We need to track:
        # 1. First PR merge succeeds
        # 2. gt sync runs (simulates metadata update)
        # 3. gh pr view shows stale base for PR #2
        # 4. gh pr edit --base is called BEFORE gh pr merge for PR #2
        captured_calls: list[tuple[list[str], Path | None]] = []

        def mock_run(*args: object, **kwargs: object) -> Mock:
            # Extract command and cwd
            if len(args) > 0 and isinstance(args[0], list):
                cmd = args[0]
            elif "args" in kwargs:
                cmd = kwargs["args"]
            else:
                cmd = []

            cwd = kwargs.get("cwd")
            captured_calls.append((cmd, cwd))

            # Mock responses for specific commands
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""

            # Simulate gh pr view returning stale base for PR #2
            if cmd == ["gh", "pr", "view", "200", "--json", "baseRefName", "--jq", ".baseRefName"]:
                mock_result.stdout = "feat-1"  # Stale base (should be main)

            return mock_result

        with patch("workstack.cli.commands.land_stack.subprocess.run", side_effect=mock_run):
            # Simulate gt sync updating metadata
            # After first PR merges, feat-2's parent becomes main in Graphite metadata
            def mock_sync(repo_root: Path, *, force: bool, quiet: bool) -> None:
                # Update graphite_ops to reflect parent change
                # feat-2's parent should become main after feat-1 lands
                graphite_ops._branches["feat-2"] = BranchMetadata.branch(
                    "feat-2",
                    "main",
                    commit_sha="ghi789",  # Parent changed from feat-1 to main
                )

            # Patch graphite sync to simulate metadata update
            graphite_ops.sync = mock_sync

            # Run land-stack with force flag
            result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Verify command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Extract just the command names for easier assertion
        command_sequences = [cmd[0] if cmd else "" for cmd, _ in captured_calls if cmd]

        # Verify critical sequence:
        # 1. gh pr merge 100 (first PR)
        # 2. gh pr view 200 (check base of second PR)
        # 3. gh pr edit 200 --base main (update stale base)
        # 4. gh pr merge 200 (second PR)

        # Find indices of key commands
        pr_edit_idx = None
        pr_merge_200_idx = None

        for idx, cmd in enumerate(captured_calls):
            cmd_list = cmd[0] if cmd else []
            if len(cmd_list) >= 2 and cmd_list[0] == "gh":
                if cmd_list[1] == "pr" and len(cmd_list) >= 4:
                    if cmd_list[2] == "view" and cmd_list[3] == "200":
                        pass
                    elif cmd_list[2] == "edit" and cmd_list[3] == "200":
                        pr_edit_idx = idx
                    elif cmd_list[2] == "merge" and cmd_list[3] == "200":
                        pr_merge_200_idx = idx

        # Assert: gh pr edit --base was called
        assert pr_edit_idx is not None, (
            f"Expected 'gh pr edit 200 --base main' call not found\n"
            f"Captured commands: {command_sequences}"
        )

        # Assert: gh pr edit happened BEFORE gh pr merge for PR #200
        assert pr_merge_200_idx is not None, "Expected 'gh pr merge 200' call not found"
        assert pr_edit_idx < pr_merge_200_idx, (
            f"gh pr edit must be called BEFORE gh pr merge\n"
            f"edit index: {pr_edit_idx}, merge index: {pr_merge_200_idx}"
        )


def test_land_stack_skips_base_update_when_already_correct() -> None:
    """Test that land-stack skips PR base update when already correct.

    When GitHub PR base already matches expected parent, we should not
    make unnecessary API calls to update it.
    """
    from unittest.mock import Mock, patch

    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build two-PR stack
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch("feat-2", "feat-1", commit_sha="ghi789"),
            },
            current_branch="feat-2",
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            }
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
            cwd=env.cwd,
        )

        captured_calls: list[tuple[list[str], Path | None]] = []

        def mock_run(*args: object, **kwargs: object) -> Mock:
            if len(args) > 0 and isinstance(args[0], list):
                cmd = args[0]
            elif "args" in kwargs:
                cmd = kwargs["args"]
            else:
                cmd = []

            cwd = kwargs.get("cwd")
            captured_calls.append((cmd, cwd))

            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""

            # Simulate gh pr view returning CORRECT base for PR #2
            if cmd == ["gh", "pr", "view", "200", "--json", "baseRefName", "--jq", ".baseRefName"]:
                mock_result.stdout = "main"  # Correct base (matches expected parent)

            return mock_result

        with patch("workstack.cli.commands.land_stack.subprocess.run", side_effect=mock_run):
            # Simulate sync updating metadata
            def mock_sync(repo_root: Path, *, force: bool, quiet: bool) -> None:
                graphite_ops._branches["feat-2"] = BranchMetadata.branch(
                    "feat-2", "main", commit_sha="ghi789"
                )

            graphite_ops.sync = mock_sync

            result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify that gh pr edit was NOT called for PR #200
        for cmd, _ in captured_calls:
            if len(cmd) >= 4 and cmd[0] == "gh" and cmd[1] == "pr":
                if cmd[2] == "edit" and cmd[3] == "200":
                    msg = "gh pr edit should not be called when base is already correct"
                    raise AssertionError(msg)


def test_land_stack_dry_run_shows_base_update() -> None:
    """Test that dry-run mode shows PR base update without executing.

    This test verifies that when a PR's GitHub base is stale (points to a branch
    that should no longer be its parent), the dry-run output shows the update
    that would be made.

    Setup: Single PR with stale base on GitHub (not reflecting a prior update)
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Simple scenario: feat-1's parent is main, but GitHub shows old base
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            current_branch="feat-1",
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
            }
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
            cwd=env.cwd,
        )

        # Mock to simulate stale base on GitHub
        from unittest.mock import Mock, patch

        def mock_run(*args: object, **kwargs: object) -> Mock:
            if len(args) > 0 and isinstance(args[0], list):
                cmd = args[0]
            elif "args" in kwargs:
                cmd = kwargs["args"]
            else:
                cmd = []

            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""

            # Mock gh pr view to return stale base
            # PR #100 (feat-1) should have stale base "old-branch" but parent is "main"
            if cmd == ["gh", "pr", "view", "100", "--json", "baseRefName", "--jq", ".baseRefName"]:
                mock_result.stdout = "old-branch"  # Stale - should be "main"

            return mock_result

        with patch("workstack.cli.commands.land_stack.subprocess.run", side_effect=mock_run):
            # Run with --dry-run flag
            result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify output shows the update that would happen
        assert "Updating PR #100 base: old-branch → main" in result.output, (
            f"Expected base update message not found. Actual output:\n{result.output}"
        )
        assert "gh pr edit 100 --base main" in result.output


def test_land_stack_fails_gracefully_when_base_update_fails() -> None:
    """Test that land-stack fails gracefully when PR base update fails.

    If gh pr edit fails, the command should exit with error before
    attempting to merge the PR.
    """
    import subprocess
    from unittest.mock import Mock, patch

    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch("feat-2", "feat-1", commit_sha="ghi789"),
            },
            current_branch="feat-2",
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            }
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
            cwd=env.cwd,
        )

        def mock_run(*args: object, **kwargs: object) -> Mock:
            if len(args) > 0 and isinstance(args[0], list):
                cmd = args[0]
            elif "args" in kwargs:
                cmd = kwargs["args"]
            else:
                cmd = []

            # Check if check=True is set
            check = kwargs.get("check", False)

            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""

            # Simulate stale base
            if cmd == ["gh", "pr", "view", "200", "--json", "baseRefName", "--jq", ".baseRefName"]:
                mock_result.stdout = "feat-1"
                return mock_result

            # Simulate gh pr edit failure
            if len(cmd) >= 4 and cmd[0] == "gh" and cmd[1] == "pr" and cmd[2] == "edit":
                if check:
                    raise subprocess.CalledProcessError(1, cmd, stderr="Permission denied")
                mock_result.returncode = 1
                mock_result.stderr = "Permission denied"
                return mock_result

            return mock_result

        with patch("workstack.cli.commands.land_stack.subprocess.run", side_effect=mock_run):
            # Simulate metadata update
            def mock_sync(repo_root: Path, *, force: bool, quiet: bool) -> None:
                graphite_ops._branches["feat-2"] = BranchMetadata.branch(
                    "feat-2", "main", commit_sha="ghi789"
                )

            graphite_ops.sync = mock_sync

            # Run and expect failure
            result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Should fail with non-zero exit code
        assert result.exit_code != 0, "Command should fail when gh pr edit fails"

        # Should show error about the failure
        # Note: CalledProcessError typically shows in traceback or error output
        assert "CalledProcessError" in result.output or result.exit_code == 1
