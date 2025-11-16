"""Centralized test environment helpers for simulating workstack scenarios.

This module provides helpers for setting up realistic workstack test environments
with Click's CliRunner. It provides two patterns:

1. simulated_workstack_env(): Filesystem-based (uses isolated_filesystem(),
   creates real directories)
2. pure_workstack_env(): In-memory (uses fakes only, no filesystem I/O)

Key Components:
    - SimulatedWorkstackEnv: Helper class for filesystem-based testing
    - PureWorkstackEnv: Helper class for in-memory testing
    - simulated_workstack_env(): Context manager for filesystem-based tests
    - pure_workstack_env(): Context manager for in-memory tests

Usage Pattern:

    Before (raw isolated_filesystem pattern - 20-30 lines per test):
    ```python
    def test_something() -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            cwd = Path.cwd()
            git_dir = cwd / ".git"
            git_dir.mkdir()
            erk_root = cwd / "workstacks"
            erk_root.mkdir()

            git_ops = FakeGitOps(git_common_dirs={cwd: git_dir})
            global_config_ops = GlobalConfig(...)
            test_ctx = ErkContext.for_test(cwd=cwd, ...)

            result = runner.invoke(cli, ["command"], obj=test_ctx)
    ```

    After (using simulated_workstack_env - ~10 lines per test):
    ```python
    def test_something() -> None:
        runner = CliRunner()
        with simulated_workstack_env(runner) as env:
            git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
            global_config_ops = GlobalConfig(...)
            script_writer=env.script_writer,
            test_ctx = ErkContext.for_test(cwd=env.cwd, ...)

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

            script_writer=env.script_writer,
            test_ctx = ErkContext.for_test(cwd=env.cwd, git_ops=git_ops, ...)
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

from erk.core.context import ErkContext
from erk.core.gitops import WorktreeInfo
from erk.core.global_config import GlobalConfig
from erk.core.graphite_ops import BranchMetadata
from erk.core.repo_discovery import RepoContext
from erk.core.script_writer import RealScriptWriterOps
from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.script_writer import FakeScriptWriterOps


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
        erk_root: Path to workstacks directory (parallel to root)
        script_writer: RealScriptWriterOps for creating actual temp files
        repo: RepoContext computed from root_worktree and erk_root
    """

    def __init__(self, root_worktree: Path, erk_root: Path) -> None:
        """Initialize test environment.

        Args:
            root_worktree: Path to root worktree (has .git/ directory)
            erk_root: Path to workstacks directory (parallel to root)
        """
        self.root_worktree = root_worktree
        self.erk_root = erk_root
        self.script_writer = RealScriptWriterOps()
        self._linked_worktrees: dict[str, Path] = {}  # Track branch -> worktree path
        self._repo = RepoContext(
            root=root_worktree,
            repo_name=root_worktree.name,
            repo_dir=erk_root / root_worktree.name,
            worktrees_dir=erk_root / root_worktree.name / "worktrees",
        )

    @property
    def cwd(self) -> Path:
        """Current working directory (convenience property)."""
        return self.root_worktree

    @property
    def git_dir(self) -> Path:
        """Path to .git directory (convenience property)."""
        return self.root_worktree / ".git"

    @property
    def repo(self) -> RepoContext:
        """RepoContext constructed from root worktree paths."""
        return self._repo

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
        linked_wt = self.erk_root / "repo" / name
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

    def build_context(
        self,
        *,
        use_graphite: bool = False,
        show_pr_info: bool = True,
        git_ops: FakeGitOps | None = None,
        graphite_ops: FakeGraphiteOps | None = None,
        github_ops: FakeGitHubOps | None = None,
        repo: RepoContext | None = None,
        **kwargs,
    ) -> ErkContext:
        """Build ErkContext with sensible defaults for testing.

        This helper eliminates boilerplate by providing default ops and config
        for tests that don't need custom setup. Custom values can be provided
        via keyword arguments.

        Args:
            use_graphite: Enable Graphite integration (default: False)
            show_pr_info: Show PR information (default: True)
            git_ops: Custom FakeGitOps (default: minimal git_common_dirs setup)
            graphite_ops: Custom FakeGraphiteOps (default: empty)
            github_ops: Custom FakeGitHubOps (default: empty)
            repo: Custom RepoContext (default: None)
            **kwargs: Additional ErkContext.for_test() parameters

        Returns:
            ErkContext configured for testing

        Example:
            ```python
            with simulated_workstack_env(runner) as env:
                # Simple case - use all defaults
                ctx = env.build_context()

                # Custom git ops with branches
                git_ops, graphite_ops = env.build_ops_from_branches(...)
                ctx = env.build_context(git_ops=git_ops, graphite_ops=graphite_ops)

                # Enable Graphite with custom config
                ctx = env.build_context(use_graphite=True)
            ```
        """
        # Determine repo to use (either provided or default)
        if repo is None:
            repo = self._repo

        # Create default ops if not provided, or ensure existing paths are set
        if git_ops is None:
            git_ops = FakeGitOps(
                git_common_dirs={self.cwd: self.git_dir},
                existing_paths={
                    self.cwd,
                    self.git_dir,
                    self.erk_root,
                    repo.root,
                    repo.repo_dir,
                },
            )
        else:
            # git_ops was provided - ensure it has necessary existing paths
            # for discover_repo_context to work correctly
            from erk.core.gitops import NoopGitOps

            unwrapped_ops = git_ops._wrapped if isinstance(git_ops, NoopGitOps) else git_ops

            # Add core paths to existing_paths if they're actually git repos
            # Only add paths that are in git_common_dirs (actual repos)
            has_existing = hasattr(unwrapped_ops, "_existing_paths")
            has_git_common = hasattr(unwrapped_ops, "_git_common_dirs")
            has_worktrees = hasattr(unwrapped_ops, "_worktrees")
            if has_existing and has_git_common:
                # Determine which cwd to use (custom or default)
                effective_cwd = kwargs.get("cwd", self.cwd)

                # Collect core paths - always include cwd and workstacks_root
                core_paths = {
                    self.cwd,
                    effective_cwd,
                    self.erk_root,
                    repo.repo_dir,
                }

                # Only add git_dir and repo.root if this is actually a git repo
                # (i.e., git_common_dirs is not empty)
                if unwrapped_ops._git_common_dirs:
                    core_paths.update({self.git_dir, repo.root})

                # Also add all worktree paths from git_ops
                if has_worktrees:
                    for worktree_list in unwrapped_ops._worktrees.values():
                        for wt_info in worktree_list:
                            core_paths.add(wt_info.path)

                unwrapped_ops._existing_paths.update(core_paths)

        if graphite_ops is None:
            graphite_ops = FakeGraphiteOps()

        if github_ops is None:
            github_ops = FakeGitHubOps()

        # Create global config if not provided in kwargs
        if "global_config" in kwargs:
            # Use the provided global_config (might be None for init tests)
            global_config = kwargs.pop("global_config")
        else:
            # Create default global config
            global_config = GlobalConfig(
                use_graphite=use_graphite,
                show_pr_info=show_pr_info,
                shell_setup_complete=False,
                erk_root=self.erk_root,
            )

        # Build and return context
        # Default cwd and script_writer to env values unless overridden in kwargs
        if "cwd" not in kwargs:
            kwargs["cwd"] = self.cwd
        if "script_writer" not in kwargs:
            kwargs["script_writer"] = self.script_writer

        # Filter out workstacks_root - it's already set in global_config above
        # Tests shouldn't override it via kwargs
        if "erk_root" in kwargs:
            kwargs.pop("erk_root")

        # Filter out trunk_branch - it's now a computed property based on git_ops
        if "trunk_branch" in kwargs:
            kwargs.pop("trunk_branch")

        return ErkContext.for_test(
            git_ops=git_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            global_config=global_config,
            repo=repo,
            **kwargs,
        )

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
                # env.script_writer is available (RealScriptWriterOps for temp files)
                git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
                test_ctx = ErkContext.for_test(
                    cwd=env.cwd,
                    script_writer=env.script_writer,
                    ...
                )
        ```
    """
    with runner.isolated_filesystem():
        base = Path.cwd()  # isolated_filesystem() creates temp dir and changes cwd to it

        # Create root worktree with .git directory
        root_worktree = base / "repo"
        root_worktree.mkdir()
        (root_worktree / ".git").mkdir()

        # Create workstacks directory
        erk_root = base / "workstacks"
        erk_root.mkdir()

        # Default to root worktree
        os.chdir(root_worktree)

        yield SimulatedWorkstackEnv(
            root_worktree=root_worktree,
            erk_root=erk_root,
        )


class PureWorkstackEnv:
    """Helper for pure in-memory testing without filesystem I/O.

    Use this for tests that verify command logic without needing
    actual filesystem operations. This is faster and simpler than
    simulated_workstack_env() for tests that don't need real directories.

    Attributes:
        cwd: Sentinel path representing current working directory
        git_dir: Sentinel path representing .git directory
        erk_root: Sentinel path for workstacks directory
        script_writer: FakeScriptWriterOps for in-memory script verification
        repo: RepoContext computed from cwd and erk_root
    """

    def __init__(
        self,
        cwd: Path,
        git_dir: Path,
        erk_root: Path,
        script_writer: FakeScriptWriterOps,
    ) -> None:
        """Initialize pure test environment.

        Args:
            cwd: Sentinel path for current working directory
            git_dir: Sentinel path for .git directory
            erk_root: Sentinel path for workstacks directory
            script_writer: FakeScriptWriterOps instance for script verification
        """
        self.cwd = cwd
        self.git_dir = git_dir
        self.erk_root = erk_root
        self.script_writer = script_writer
        self._linked_worktrees: dict[str, Path] = {}  # Track branch -> worktree path
        repo_dir = erk_root / "repos" / cwd.name
        self._repo = RepoContext(
            root=cwd,
            repo_name=cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

    @property
    def repo(self) -> RepoContext:
        """RepoContext constructed from sentinel paths."""
        return self._repo

    @property
    def root_worktree(self) -> Path:
        """Alias for cwd for compatibility with SimulatedWorkstackEnv."""
        return self.cwd

    def build_context(
        self,
        *,
        use_graphite: bool = False,
        show_pr_info: bool = True,
        git_ops: FakeGitOps | None = None,
        graphite_ops: FakeGraphiteOps | None = None,
        github_ops: FakeGitHubOps | None = None,
        repo: RepoContext | None = None,
        existing_paths: set[Path] | None = None,
        file_contents: dict[Path, str] | None = None,
        **kwargs,
    ) -> ErkContext:
        """Build ErkContext with sensible defaults for testing.

        This helper eliminates boilerplate by providing default ops and config
        for tests that don't need custom setup. Custom values can be provided
        via keyword arguments.

        Args:
            use_graphite: Enable Graphite integration (default: False)
            show_pr_info: Show PR information (default: True)
            git_ops: Custom FakeGitOps (default: minimal git_common_dirs setup)
            graphite_ops: Custom FakeGraphiteOps (default: empty)
            github_ops: Custom FakeGitHubOps (default: empty)
            repo: Custom RepoContext (default: None)
            existing_paths: Set of sentinel paths to treat as existing (pure mode only)
            file_contents: Mapping of sentinel paths to file content (pure mode only)
            **kwargs: Additional ErkContext.for_test() parameters

        Returns:
            ErkContext configured for testing

        Example:
            ```python
            with pure_workstack_env(runner) as env:
                # Simple case - use all defaults
                ctx = env.build_context()

                # Enable Graphite with custom config
                ctx = env.build_context(use_graphite=True)

                # With existing paths for pure mode testing
                ctx = env.build_context(
                    existing_paths={Path("/test/repo/.workstack")},
                    file_contents={Path("/test/repo/.PLAN.md"): "plan content"},
                )
            ```
        """
        # Determine repo to use (either provided or default)
        if repo is None:
            repo = self._repo

        # Create default ops if not provided
        if git_ops is None:
            # Automatically include core sentinel paths in existing_paths
            # so that repo discovery and other path checks work correctly
            # Include repo.root and repo.workstacks_dir so os.walk() and path checks succeed
            core_paths = {
                self.cwd,
                self.git_dir,
                self.erk_root,
                repo.root,
                repo.repo_dir,
            }
            all_existing = core_paths | (existing_paths or set())

            git_ops = FakeGitOps(
                git_common_dirs={self.cwd: self.git_dir},
                existing_paths=all_existing,
                file_contents=file_contents or {},
            )
        else:
            # git_ops was provided - extract worktree paths and merge with existing_paths
            # Unwrap NoopGitOps if needed to access underlying FakeGitOps
            from erk.core.gitops import NoopGitOps

            unwrapped_ops = git_ops._wrapped if isinstance(git_ops, NoopGitOps) else git_ops
            worktree_paths = {
                wt.path for worktrees in unwrapped_ops._worktrees.values() for wt in worktrees
            }
            # Determine which cwd to use (custom or default)
            effective_cwd = kwargs.get("cwd", self.cwd)

            core_paths = {
                self.cwd,
                effective_cwd,
                self.git_dir,
                self.erk_root,
                repo.root,
                repo.repo_dir,
            }
            all_existing = core_paths | worktree_paths | (existing_paths or set())

            # Mutate existing ops instance instead of recreating
            # This preserves mutation tracking for test assertions
            unwrapped_ops._existing_paths.update(all_existing)
            if file_contents:
                unwrapped_ops._file_contents.update(file_contents)

        if graphite_ops is None:
            graphite_ops = FakeGraphiteOps()

        if github_ops is None:
            github_ops = FakeGitHubOps()

        # Create global config if not provided in kwargs
        if "global_config" in kwargs:
            # Use the provided global_config (might be None for init tests)
            global_config = kwargs.pop("global_config")
        else:
            # Create default global config
            global_config = GlobalConfig(
                use_graphite=use_graphite,
                show_pr_info=show_pr_info,
                shell_setup_complete=False,
                erk_root=self.erk_root,
            )

        # Build and return context
        # Default cwd and script_writer to env values unless overridden in kwargs
        if "cwd" not in kwargs:
            kwargs["cwd"] = self.cwd
        if "script_writer" not in kwargs:
            kwargs["script_writer"] = self.script_writer

        # Filter out workstacks_root - it's already set in global_config above
        # Tests shouldn't override it via kwargs
        if "erk_root" in kwargs:
            kwargs.pop("erk_root")

        # Filter out trunk_branch - it's now a computed property based on git_ops
        if "trunk_branch" in kwargs:
            kwargs.pop("trunk_branch")

        return ErkContext.for_test(
            git_ops=git_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            global_config=global_config,
            repo=repo,
            **kwargs,
        )

    def create_linked_worktree(self, name: str, branch: str, *, chdir: bool = False) -> Path:
        """Create a linked worktree (sentinel path only, no filesystem).

        Args:
            name: Worktree directory name
            branch: Branch to checkout in the worktree
            chdir: Ignored in pure mode (no actual directory change)

        Returns:
            Sentinel path for the worktree
        """
        # Create sentinel path (no mkdir needed)
        linked_wt = self.erk_root / self.cwd.name / name
        # Track it
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

        # Collect all worktree paths as existing
        existing_paths = {wt.path for wt in worktrees_list} | {self.cwd, self.git_dir}

        git_ops = FakeGitOps(
            worktrees={self.root_worktree: worktrees_list},
            current_branches=current_branches_map,
            git_common_dirs=git_common_dirs_map,
            existing_paths=existing_paths,
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

        while current is not None:
            stack.insert(0, current)
            parent = branches[current].parent
            current = parent

        return stack


@contextmanager
def pure_workstack_env(
    runner: CliRunner,
    *,
    branches: list[BranchMetadata] | None = None,
) -> Generator[PureWorkstackEnv]:
    """Create pure in-memory test environment without filesystem I/O.

    This context manager provides a faster alternative to simulated_workstack_env()
    for tests that don't need actual filesystem operations. It uses sentinel paths
    and in-memory fakes exclusively.

    Sentinel paths throw errors if filesystem operations are attempted (.exists(),
    .resolve(), .mkdir(), etc.), enforcing that all checks go through fake operations
    for high test fidelity.

    Use this when:
    - Testing command logic that doesn't depend on real directories
    - Verifying script content without creating temp files
    - Running tests faster without filesystem overhead

    Use simulated_workstack_env() when:
    - Testing actual worktree creation/removal
    - Verifying git integration with real directories
    - Testing filesystem-dependent features

    Args:
        runner: Click CliRunner instance (not used, but kept for API consistency)
        branches: Optional branch metadata for initializing git state

    Yields:
        PureWorkstackEnv with sentinel paths and in-memory fakes

    Example:
        ```python
        def test_jump_pure() -> None:
            runner = CliRunner()
            with pure_workstack_env(runner) as env:
                # No filesystem I/O, all operations in-memory
                git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
                ctx = ErkContext.for_test(
                    cwd=env.cwd,
                    git_ops=git_ops,
                    script_writer=env.script_writer,
                )
                result = runner.invoke(cli, ["jump", "feature", "--script"], obj=ctx)

                # Verify script content in-memory
                script_path = Path(result.stdout.strip())
                content = env.script_writer.get_script_content(script_path)
                assert content is not None
        ```
    """
    from tests.test_utils import sentinel_path

    # Use sentinel paths that throw on filesystem operations
    cwd = sentinel_path("/test/repo")
    git_dir = sentinel_path("/test/repo/.git")
    erk_root = sentinel_path("/test/workstacks")

    # Create in-memory script writer
    script_writer = FakeScriptWriterOps()

    # No isolated_filesystem(), no os.chdir(), no mkdir()
    try:
        yield PureWorkstackEnv(
            cwd=cwd,
            git_dir=git_dir,
            erk_root=erk_root,
            script_writer=script_writer,
        )
    finally:
        # Clear SentinelPath file storage for test isolation
        from tests.test_utils.paths import SentinelPath

        SentinelPath.clear_file_storage()
