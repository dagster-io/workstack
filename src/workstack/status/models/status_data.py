"""Data models for status information."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorktreeDisplayInfo:
    """Worktree information for display/presentation purposes.

    This represents worktree data for status rendering and display.
    For infrastructure-layer worktree data, see workstack.core.gitops.WorktreeInfo.
    """

    name: str
    path: Path
    branch: str | None
    is_root: bool

    @staticmethod
    def root(path: Path, branch: str = "main", name: str = "root") -> "WorktreeDisplayInfo":
        """Create root worktree for test display.

        Args:
            path: Path to the root worktree
            branch: Branch name (default: "main")
            name: Display name (default: "root")

        Returns:
            WorktreeDisplayInfo with is_root=True

        Example:
            Before (4 lines):
                worktree = WorktreeDisplayInfo(
                    name="root", path=repo_root, branch="main", is_root=True
                )

            After (1 line):
                worktree = WorktreeDisplayInfo.root(repo_root)
        """
        return WorktreeDisplayInfo(path=path, branch=branch, is_root=True, name=name)

    @staticmethod
    def feature(path: Path, branch: str, name: str | None = None) -> "WorktreeDisplayInfo":
        """Create feature worktree for test display.

        Args:
            path: Path to the feature worktree
            branch: Branch name
            name: Display name (default: uses path.name)

        Returns:
            WorktreeDisplayInfo with is_root=False

        Example:
            Before (4 lines):
                worktree = WorktreeDisplayInfo(
                    name="my-feature", path=feature_wt, branch="feature", is_root=False
                )

            After (1 line):
                worktree = WorktreeDisplayInfo.feature(feature_wt, "feature")
        """
        display_name = name if name else path.name
        return WorktreeDisplayInfo(path=path, branch=branch, is_root=False, name=display_name)


@dataclass(frozen=True)
class CommitInfo:
    """Information about a git commit."""

    sha: str
    message: str
    author: str
    date: str


@dataclass(frozen=True)
class GitStatus:
    """Git repository status information."""

    branch: str | None
    clean: bool
    ahead: int
    behind: int
    staged_files: list[str]
    modified_files: list[str]
    untracked_files: list[str]
    recent_commits: list[CommitInfo]


@dataclass(frozen=True)
class StackPosition:
    """Graphite stack position information."""

    stack: list[str]
    current_branch: str
    parent_branch: str | None
    children_branches: list[str]
    is_trunk: bool


@dataclass(frozen=True)
class PullRequestStatus:
    """Pull request status information."""

    number: int
    title: str | None  # May not be available from all data sources
    state: str
    is_draft: bool
    url: str
    checks_passing: bool | None
    reviews: list[str] | None  # May not be available from all data sources
    ready_to_merge: bool


@dataclass(frozen=True)
class EnvironmentStatus:
    """Environment variables status."""

    variables: dict[str, str]


@dataclass(frozen=True)
class DependencyStatus:
    """Dependency status for various language ecosystems."""

    language: str
    up_to_date: bool
    outdated_count: int
    details: str | None


@dataclass(frozen=True)
class PlanStatus:
    """Status of .PLAN.md file."""

    exists: bool
    path: Path | None
    summary: str | None
    line_count: int
    first_lines: list[str]


@dataclass(frozen=True)
class StatusData:
    """Container for all status information."""

    worktree_info: WorktreeDisplayInfo
    git_status: GitStatus | None
    stack_position: StackPosition | None
    pr_status: PullRequestStatus | None
    environment: EnvironmentStatus | None
    dependencies: DependencyStatus | None
    plan: PlanStatus | None
    related_worktrees: list[WorktreeDisplayInfo]
