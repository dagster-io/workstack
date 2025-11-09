"""Shared test utilities for setting up repository environments.

This module provides helpers for creating simulated workstack test environments
that mimic real git worktree structures without requiring actual git operations.
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

    This class creates a realistic directory structure for testing worktree
    operations without requiring actual git commands. It automatically:

    - Creates proper .git directory structure
    - Manages linked worktrees with correct .git file pointers
    - Builds FakeGitOps and FakeGraphiteOps from branch metadata
    - Computes stacks from parent/child relationships

    Example usage:
        ```python
        runner = CliRunner()
        with simulated_workstack_env(runner) as env:
            # Create linked worktrees
            env.create_linked_worktree("feat-1", "feat-1", chdir=False)
            env.create_linked_worktree("feat-2", "feat-2", chdir=False)

            # Build ops from branches
            git_ops, graphite_ops = env.build_ops_from_branches(
                {
                    "main": BranchMetadata(
                        name="main",
                        parent=None,
                        children=["feat-1"],
                        is_trunk=True,
                        commit_sha="abc123",
                    ),
                    "feat-1": BranchMetadata(
                        name="feat-1",
                        parent="main",
                        children=["feat-2"],
                        is_trunk=False,
                        commit_sha="def456",
                    ),
                    "feat-2": BranchMetadata(
                        name="feat-2",
                        parent="feat-1",
                        children=[],
                        is_trunk=False,
                        commit_sha="ghi789",
                    ),
                },
                current_branch="feat-1",
            )
        ```

    Use cases:
    - Navigation command tests (up, down, switch, jump)
    - Sync command tests (inspect and delete worktrees)
    - List command tests (display existing worktrees)

    NOT suitable for:
    - Tests that create worktrees during execution
    - Tests that need real graphite cache file I/O
    - Pure unit tests without filesystem needs
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
                    "main": BranchMetadata(
                        name="main",
                        parent=None,
                        children=["feat-1"],
                        is_trunk=True,
                        commit_sha="abc123",
                    ),
                    "feat-1": BranchMetadata(
                        name="feat-1",
                        parent="main",
                        children=["feat-2"],
                        is_trunk=False,
                        commit_sha="def456",
                    ),
                    "feat-2": BranchMetadata(
                        name="feat-2",
                        parent="feat-1",
                        children=None,
                        is_trunk=False,
                        commit_sha="ghi789",
                    ),
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
            default_branches={self.root_worktree: trunk_branch},
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

    Example:
        ```python
        runner = CliRunner()
        with simulated_workstack_env(runner) as env:
            # Create linked worktrees
            wt1 = env.create_linked_worktree("feat-1", "feat-1", chdir=False)
            wt2 = env.create_linked_worktree("feat-2", "feat-2", chdir=False)

            # Build fake ops
            git_ops, graphite_ops = env.build_ops_from_branches({
                "main": BranchMetadata(name="main", parent=None, ...),
                "feat-1": BranchMetadata(name="feat-1", parent="main", ...),
            }, current_branch="main")

            # Use in tests
            ctx = WorkstackContext(git_ops=git_ops, graphite_ops=graphite_ops, ...)
            result = runner.invoke(cli, ["up"], obj=ctx)
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
