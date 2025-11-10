"""Centralized test environment helpers for simulating workstack scenarios.

This module provides helpers for setting up realistic workstack test environments
with Click's CliRunner. It focuses on the CliRunner + isolated_filesystem() pattern,
NOT pytest's tmp_path fixture (which is handled by WorktreeScenario in conftest.py).

Key Components:
    - SimulatedWorkstackEnv: Helper class for managing test environments
    - simulated_workstack_env(): Context manager that sets up complete environment

Usage Pattern:

    Before (raw isolated_filesystem pattern - 20-30 lines per test):
    ```python
    def test_something() -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            cwd = Path.cwd()
            git_dir = cwd / ".git"
            git_dir.mkdir()
            workstacks_root = cwd / "workstacks"
            workstacks_root.mkdir()

            git_ops = FakeGitOps(git_common_dirs={cwd: git_dir})
            global_config_ops = GlobalConfig(...)
            test_ctx = WorkstackContext.for_test(cwd=cwd, ...)

            result = runner.invoke(cli, ["command"], obj=test_ctx)
    ```

    After (using simulated_workstack_env - ~10 lines per test):
    ```python
    def test_something() -> None:
        runner = CliRunner()
        with simulated_workstack_env(runner) as env:
            git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
            global_config_ops = GlobalConfig(...)
            test_ctx = WorkstackContext.for_test(cwd=env.cwd, ...)

            result = runner.invoke(cli, ["command"], obj=test_ctx)
    ```

Advanced Usage (complex worktree scenarios):
    ```python
    def test_multi_worktree_scenario() -> None:
        runner = CliRunner()
        with simulated_workstack_env(runner) as env:
            # Create linked worktrees
            env.create_linked_worktree("feat-1", "feat-1", chdir=False)
            env.create_linked_worktree("feat-2", "feat-2", chdir=True)

            # Build ops from branch metadata
            git_ops, graphite_ops = env.build_ops_from_branches(
                {
                    "main": BranchMetadata.trunk("main", children=["feat-1"]),
                    "feat-1": BranchMetadata.branch("feat-1", "main", children=["feat-2"]),
                    "feat-2": BranchMetadata.branch("feat-2", "feat-1"),
                },
                current_branch="feat-2",
            )

            test_ctx = WorkstackContext.for_test(cwd=env.cwd, git_ops=git_ops, ...)
    ```

Directory Structure Created:
    base/
      ├── repo/         (root worktree with .git/)
      └── workstacks/   (parallel to repo, initially empty)

Note: This helper is specifically for CliRunner tests. For pytest's tmp_path fixture,
use WorktreeScenario from conftest.py instead.
"""

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from click.testing import CliRunner

from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from workstack.core.gitops import WorktreeInfo
from workstack.core.graphite_ops import BranchMetadata


class SimulatedWorkstackEnv:
    """Helper for managing simulated workstack test environment.

    This class provides utilities for:
    - Managing root and linked worktrees
    - Building FakeGitOps and FakeGraphiteOps from branch metadata
    - Creating realistic git directory structures

    Attributes:
        cwd: Current working directory (initially root_worktree)
        git_dir: Path to .git directory (root_worktree / ".git")
        root_worktree: Path to root worktree (has .git/ directory)
        workstacks_root: Path to workstacks directory (parallel to root)
    """

    def __init__(self, root_worktree: Path, workstacks_root: Path) -> None:
        """Initialize test environment.

        Args:
            root_worktree: Path to root worktree (has .git/ directory)
            workstacks_root: Path to workstacks directory (parallel to root)
        """
        self.root_worktree = root_worktree
        self.workstacks_root = workstacks_root
        self._linked_worktrees: dict[str, Path] = {}  # Track branch -> worktree path

    @property
    def cwd(self) -> Path:
        """Current working directory (convenience property)."""
        return self.root_worktree

    @property
    def git_dir(self) -> Path:
        """Path to .git directory (convenience property)."""
        return self.root_worktree / ".git"

    def create_linked_worktree(self, name: str, branch: str, *, chdir: bool) -> Path:
        """Create a linked worktree in workstacks directory.

        Args:
            name: Name for the worktree directory
            branch: Branch name for the worktree
            chdir: Whether to change working directory to the new worktree (required)

        Returns:
            Path to the created linked worktree

        Example:
            ```python
            # Create but stay in root worktree
            wt1 = env.create_linked_worktree("feat-1", "feat-1", chdir=False)

            # Create and switch to it
            wt2 = env.create_linked_worktree("feat-2", "feat-2", chdir=True)
            assert Path.cwd() == wt2
            ```
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
            ```python
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
            # Now git_ops and graphite_ops are configured with full stack relationships
            ```
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

    IMPORTANT: This context manager handles runner.isolated_filesystem() internally.
    Do NOT nest this inside runner.isolated_filesystem() - that would create
    double indentation and is unnecessary.

    Args:
        runner: Click CliRunner instance

    Yields:
        SimulatedWorkstackEnv helper for managing test environment

    Example:
        ```python
        def test_something() -> None:
            runner = CliRunner()
            # Note: simulated_workstack_env() handles isolated_filesystem() internally
            with simulated_workstack_env(runner) as env:
                # env.cwd is available (root worktree)
                # env.git_dir is available (.git directory)
                git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
                test_ctx = WorkstackContext.for_test(cwd=env.cwd, ...)
        ```
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
