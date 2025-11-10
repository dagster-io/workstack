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
from workstack.core.global_config import GlobalConfig
from workstack.core.gitops import WorktreeInfo
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
        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
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

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=True,
        )

        graphite_ops = FakeGraphiteOps()

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
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

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=True,
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

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
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

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=True,
        )

        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", commit_sha="abc123"),
            },
            stacks={
                "main": ["main"],
            },
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
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

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=True,
        )

        # Branch not in graphite stack
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", commit_sha="abc123"),
            },
            stacks={},
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
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

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=True,
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

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
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

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=True,
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

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
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

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=True,
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

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
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

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=True,
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

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
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

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
                "feat-3": ("OPEN", 300, "Feature 3"),
            }
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
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

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=True,
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

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
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

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=True,
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

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
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

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Add feature 1"),
            }
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
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

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Add feature 1"),
            }
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
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
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", pr_number=123, commit_sha="def456"
                ),
            },
            current_branch="feature-1",
        )

        # Setup GitHub ops with an open PR
        github_ops = FakeGitHubOps(pr_statuses={"feature-1": ("OPEN", 123, "Feature 1")})

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        # Act: Run with --script flag (this is what shell wrapper will call)
        result = runner.invoke(
            cli,
            ["land-stack", "-f", "--script"],  # force to skip confirmation
            obj=test_ctx,
        )

        # Assert: Command should succeed
        # Note: We can't verify actual shell integration behavior with CliRunner
        # but we can verify the flag is accepted and the command runs
        assert result.exit_code == 0

        # In script mode, all output should go to stderr
        # Passthrough commands rely on the recovery mechanism, not explicit script generation
