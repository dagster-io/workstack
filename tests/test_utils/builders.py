"""Test data builders for common scenarios.

This module provides fluent APIs for building test data, reducing setup duplication
across the test suite. Use these builders instead of manually constructing complex
test scenarios.

Examples:
    # Build Graphite cache
    cache = (
        GraphiteCacheBuilder()
        .add_trunk("main", children=["feature"])
        .add_branch("feature", parent="main")
        .write_to(git_dir)
    )

    # Build PR with specific state
    pr = PullRequestInfoBuilder(123).with_failing_checks().as_draft().build()

    # Build complete test scenario
    scenario = (
        WorktreeScenario(tmp_path)
        .with_main_branch()
        .with_feature_branch("feature")
        .with_pr("feature", 123, checks_passing=True)
        .build()
    )
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps, WorktreeInfo
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from workstack.core.context import WorkstackContext
from workstack.core.github_ops import PullRequestInfo
from workstack.core.global_config import GlobalConfig


class GraphiteCacheBuilder:
    """Fluent API for building graphite cache structures.

    Use this builder to create .graphite_cache_persist files for testing without
    manually constructing the JSON structure.

    Examples:
        # Simple stack
        cache = (
            GraphiteCacheBuilder()
            .add_trunk("main")
            .add_branch("feature", parent="main")
            .build()
        )

        # Multi-level stack
        cache = (
            GraphiteCacheBuilder()
            .add_trunk("main", children=["level-1"])
            .add_branch("level-1", parent="main", children=["level-2"])
            .add_branch("level-2", parent="level-1")
            .write_to(git_dir)
        )
    """

    def __init__(self) -> None:
        """Initialize empty cache builder."""
        self._branches: list[tuple[str, dict[str, Any]]] = []
        self._trunk_branches: set[str] = set()

    def add_trunk(self, name: str, children: list[str] | None = None) -> "GraphiteCacheBuilder":
        """Add a trunk branch (main, master, develop).

        Args:
            name: Branch name
            children: Optional list of direct child branches

        Returns:
            Self for method chaining
        """
        self._trunk_branches.add(name)
        self._branches.append(
            (
                name,
                {
                    "validationResult": "TRUNK",
                    "children": children or [],
                },
            )
        )
        return self

    def add_branch(
        self, name: str, parent: str, children: list[str] | None = None
    ) -> "GraphiteCacheBuilder":
        """Add a feature branch with parent.

        Args:
            name: Branch name
            parent: Parent branch name
            children: Optional list of direct child branches

        Returns:
            Self for method chaining
        """
        self._branches.append(
            (
                name,
                {
                    "parentBranchName": parent,
                    "children": children or [],
                },
            )
        )
        return self

    def build(self) -> dict[str, Any]:
        """Build the graphite cache dictionary.

        Returns:
            Dictionary suitable for JSON serialization
        """
        return {"branches": self._branches}

    def write_to(self, git_dir: Path) -> Path:
        """Write cache to .graphite_cache_persist file.

        Args:
            git_dir: Path to .git directory

        Returns:
            Path to created cache file
        """
        cache_file = git_dir / ".graphite_cache_persist"
        cache_file.write_text(json.dumps(self.build()), encoding="utf-8")
        return cache_file


class PullRequestInfoBuilder:
    """Factory for creating PR test data with sensible defaults.

    Use this builder to create PullRequestInfo objects without manually specifying
    all fields.

    Examples:
        # PR with failing checks
        pr = PullRequestInfoBuilder(123).with_failing_checks().build()

        # Draft PR
        pr = PullRequestInfoBuilder(456).as_draft().build()

        # Merged PR
        pr = PullRequestInfoBuilder(789).as_merged().build()
    """

    def __init__(self, number: int, branch: str = "feature") -> None:
        """Initialize PR builder with required fields.

        Args:
            number: PR number
            branch: Branch name (default: "feature")
        """
        self.number = number
        self.branch = branch
        self.state = "OPEN"
        self.is_draft = False
        self.checks_passing: bool | None = None
        self.owner = "owner"
        self.repo = "repo"

    def with_passing_checks(self) -> "PullRequestInfoBuilder":
        """Configure PR with passing checks.

        Returns:
            Self for method chaining
        """
        self.checks_passing = True
        return self

    def with_failing_checks(self) -> "PullRequestInfoBuilder":
        """Configure PR with failing checks.

        Returns:
            Self for method chaining
        """
        self.checks_passing = False
        return self

    def as_draft(self) -> "PullRequestInfoBuilder":
        """Configure PR as draft.

        Returns:
            Self for method chaining
        """
        self.is_draft = True
        return self

    def as_merged(self) -> "PullRequestInfoBuilder":
        """Configure PR as merged.

        Returns:
            Self for method chaining
        """
        self.state = "MERGED"
        return self

    def as_closed(self) -> "PullRequestInfoBuilder":
        """Configure PR as closed (not merged).

        Returns:
            Self for method chaining
        """
        self.state = "CLOSED"
        return self

    def build(self) -> PullRequestInfo:
        """Build PullRequestInfo object.

        Returns:
            Configured PullRequestInfo
        """
        return PullRequestInfo(
            number=self.number,
            state=self.state,
            url=f"https://github.com/{self.owner}/{self.repo}/pull/{self.number}",
            is_draft=self.is_draft,
            checks_passing=self.checks_passing,
            owner=self.owner,
            repo=self.repo,
        )


@dataclass
class WorktreeScenario:
    """Complete test scenario with worktrees, git ops, and context.

    This builder creates a full test environment including:
    - Directory structure (repo root, workstacks directory)
    - Fake operations (git, github, graphite, shell, config)
    - WorkstackContext ready for CLI testing

    Use this when you need a complete test setup. For simpler cases, consider
    using pytest fixtures instead.

    Examples:
        # Basic scenario
        scenario = (
            WorktreeScenario(tmp_path)
            .with_main_branch()
            .with_feature_branch("my-feature")
            .build()
        )
        result = runner.invoke(cli, ["list"], obj=scenario.ctx)

        # Scenario with PR and Graphite
        scenario = (
            WorktreeScenario(tmp_path)
            .with_main_branch()
            .with_feature_branch("my-feature")
            .with_pr("my-feature", number=123, checks_passing=True)
            .with_graphite_stack(["main", "my-feature"])
            .build()
        )
    """

    base_path: Path
    repo_name: str = "repo"

    def __post_init__(self) -> None:
        """Initialize directory structure and internal state."""
        self.repo_root = self.base_path / self.repo_name
        self.git_dir = self.repo_root / ".git"
        self.workstacks_root = self.base_path / "workstacks"
        self.workstacks_dir = self.workstacks_root / self.repo_name

        self._worktrees: dict[Path, list[WorktreeInfo]] = {}
        self._git_common_dirs: dict[Path, Path] = {}
        self._current_branches: dict[Path, str | None] = {}
        self._prs: dict[str, PullRequestInfo] = {}
        self._graphite_stacks: dict[str, list[str]] = {}
        self._use_graphite = False
        self._show_pr_info = False

    def with_main_branch(self, name: str = "main") -> "WorktreeScenario":
        """Add main/root worktree.

        Args:
            name: Branch name (default: "main")

        Returns:
            Self for method chaining
        """
        self.repo_root.mkdir(parents=True, exist_ok=True)
        self.git_dir.mkdir(parents=True, exist_ok=True)

        self._worktrees.setdefault(self.repo_root, []).append(
            WorktreeInfo(path=self.repo_root, branch=name, is_root=True)
        )
        self._git_common_dirs[self.repo_root] = self.git_dir
        self._current_branches[self.repo_root] = name
        return self

    def with_feature_branch(self, name: str, parent: str = "main") -> "WorktreeScenario":
        """Add feature branch worktree.

        Args:
            name: Branch name
            parent: Parent branch name (default: "main", not used by builder
                but available for context)

        Returns:
            Self for method chaining
        """
        worktree_path = self.workstacks_dir / name
        worktree_path.mkdir(parents=True, exist_ok=True)

        self._worktrees.setdefault(self.repo_root, []).append(
            WorktreeInfo(path=worktree_path, branch=name, is_root=False)
        )
        self._git_common_dirs[worktree_path] = self.git_dir
        self._current_branches[worktree_path] = name
        return self

    def with_pr(
        self,
        branch: str,
        number: int,
        checks_passing: bool | None = None,
        is_draft: bool = False,
        state: str = "OPEN",
    ) -> "WorktreeScenario":
        """Add PR for a branch.

        Args:
            branch: Branch name
            number: PR number
            checks_passing: Optional check status
            is_draft: Whether PR is draft
            state: PR state ("OPEN", "MERGED", "CLOSED")

        Returns:
            Self for method chaining
        """
        self._show_pr_info = True
        builder = PullRequestInfoBuilder(number, branch)
        builder.state = state
        builder.is_draft = is_draft
        builder.checks_passing = checks_passing
        self._prs[branch] = builder.build()
        return self

    def with_graphite_stack(self, branches: list[str]) -> "WorktreeScenario":
        """Add Graphite stack for a branch (last branch is current).

        Args:
            branches: List of branch names from trunk to current

        Returns:
            Self for method chaining
        """
        self._use_graphite = True
        current_branch = branches[-1]
        self._graphite_stacks[current_branch] = branches
        return self

    def build(self) -> "WorktreeScenario":
        """Build the scenario and create fakes.

        Returns:
            Self with ctx attribute populated
        """
        self.git_ops = FakeGitOps(
            worktrees=self._worktrees,
            git_common_dirs=self._git_common_dirs,
            current_branches=self._current_branches,
        )

        self.github_ops = FakeGitHubOps(prs=self._prs)

        self.graphite_ops = FakeGraphiteOps(stacks=self._graphite_stacks)

        global_config = GlobalConfig(
            workstacks_root=self.workstacks_root,
            use_graphite=self._use_graphite,
            shell_setup_complete=False,
            show_pr_info=self._show_pr_info,
        )

        self.shell_ops = FakeShellOps()

        self.ctx = WorkstackContext.for_test(
            git_ops=self.git_ops,
            global_config=global_config,
            github_ops=self.github_ops,
            graphite_ops=self.graphite_ops,
            shell_ops=self.shell_ops,
            cwd=self.repo_root,
            dry_run=False,
        )

        return self
