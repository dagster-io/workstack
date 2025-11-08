"""High-level Graphite operations interface.

This module provides a clean abstraction over Graphite CLI (gt) calls, making the
codebase more testable and maintainable.

Architecture:
- GraphiteOps: Abstract base class defining the interface
- RealGraphiteOps: Production implementation using gt CLI
"""

import json
import subprocess
import sys
import warnings
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from workstack.core.branch_metadata import BranchMetadata
from workstack.core.github_ops import PullRequestInfo, _parse_github_pr_url
from workstack.core.gitops import GitOps


def read_graphite_json_file(file_path: Path, description: str) -> dict[str, Any]:
    """Read and parse a Graphite JSON file.

    Args:
        file_path: Path to the JSON file (must exist)
        description: Human-readable description for error messages
            (e.g., "Graphite cache", "Graphite PR info")

    Returns:
        Parsed JSON dict

    Raises:
        FileNotFoundError: If file doesn't exist
        OSError: If file cannot be read
        json.JSONDecodeError: If JSON is invalid (warning emitted before raising)

    Note:
        Callers must check file_path.exists() before calling if they want
        to handle missing files gracefully.

        When JSON parsing fails, a UserWarning is emitted before the
        JSONDecodeError is re-raised to provide context about the failure.
    """
    json_str = file_path.read_text(encoding="utf-8")
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        warnings.warn(f"Cannot parse {description} at {file_path}: Invalid JSON", stacklevel=2)
        raise


def parse_graphite_pr_info(json_str: str) -> dict[str, PullRequestInfo]:
    """Parse Graphite's .graphite_pr_info JSON into PullRequestInfo objects.

    Args:
        json_str: JSON string from .graphite_pr_info file

    Returns:
        Mapping of branch name to PullRequestInfo
    """
    data = json.loads(json_str)
    prs = {}

    for pr in data.get("prInfos", []):
        branch = pr["headRefName"]

        graphite_url = pr["url"]
        github_url = _graphite_url_to_github_url(graphite_url)
        parsed = _parse_github_pr_url(github_url)
        if parsed is None:
            continue
        owner, repo = parsed

        prs[branch] = PullRequestInfo(
            number=pr["prNumber"],
            state=pr["state"],
            url=github_url,
            is_draft=pr["isDraft"],
            checks_passing=None,  # CI status not available from Graphite cache
            owner=owner,
            repo=repo,
        )

    return prs


def parse_graphite_cache(
    json_str: str, git_branch_heads: dict[str, str]
) -> dict[str, BranchMetadata]:
    """Parse Graphite's .graphite_cache_persist JSON into BranchMetadata objects.

    Args:
        json_str: JSON string from .graphite_cache_persist file
        git_branch_heads: Mapping of branch name to commit SHA from git

    Returns:
        Mapping of branch name to BranchMetadata
    """
    cache_data = json.loads(json_str)
    branches_data: list[tuple[str, dict[str, object]]] = cache_data.get("branches", [])

    result = {}
    for branch_name, info in branches_data:
        if not isinstance(info, dict):
            continue

        # Get commit SHA from git (not stored in cache)
        commit_sha = git_branch_heads.get(branch_name, "")

        parent = info.get("parentBranchName")
        if not isinstance(parent, str | None):
            parent = None

        children_raw = info.get("children", [])
        if not isinstance(children_raw, list):
            children_raw = []
        children = [c for c in children_raw if isinstance(c, str)]

        is_trunk = info.get("validationResult") == "TRUNK"

        result[branch_name] = BranchMetadata(
            name=branch_name,
            parent=parent,
            children=children,
            is_trunk=is_trunk,
            commit_sha=commit_sha,
        )

    return result


def _graphite_url_to_github_url(graphite_url: str) -> str:
    """Convert Graphite URL to GitHub URL.

    Input: https://app.graphite.dev/github/pr/dagster-io/workstack/42
    Output: https://github.com/dagster-io/workstack/pull/42
    """
    parts = graphite_url.split("/")
    if len(parts) >= 8 and parts[2] == "app.graphite.dev":
        owner = parts[5]
        repo = parts[6]
        pr_number = parts[7]
        return f"https://github.com/{owner}/{repo}/pull/{pr_number}"
    return graphite_url


class GraphiteOps(ABC):
    """Abstract interface for Graphite operations.

    All implementations (real and fake) must implement this interface.
    """

    @abstractmethod
    def get_graphite_url(self, owner: str, repo: str, pr_number: int) -> str:
        """Get Graphite PR URL for a pull request.

        Args:
            owner: GitHub repository owner (e.g., "dagster-io")
            repo: GitHub repository name (e.g., "workstack")
            pr_number: GitHub PR number

        Returns:
            Graphite PR URL (e.g., "https://app.graphite.dev/github/pr/dagster-io/workstack/23")
        """
        ...

    @abstractmethod
    def sync(self, repo_root: Path, *, force: bool, quiet: bool) -> None:
        """Run gt sync to synchronize with remote.

        Args:
            repo_root: Repository root directory
            force: If True, pass --force flag to gt sync
            quiet: If True, pass --quiet flag to gt sync for minimal output
        """
        ...

    @abstractmethod
    def get_prs_from_graphite(self, git_ops: GitOps, repo_root: Path) -> dict[str, PullRequestInfo]:
        """Get PR information from Graphite's local cache.

        Reads .git/.graphite_pr_info and returns PR data in the same format
        as GitHubOps.get_prs_for_repo() for compatibility.

        Args:
            git_ops: GitOps instance for accessing git common directory
            repo_root: Repository root directory

        Returns:
            Mapping of branch name -> PullRequestInfo
            - checks_passing is always None (CI status not available)
            - Empty dict if .graphite_pr_info doesn't exist
        """
        ...

    @abstractmethod
    def get_all_branches(self, git_ops: GitOps, repo_root: Path) -> dict[str, BranchMetadata]:
        """Get all gt-tracked branches with metadata.

        Reads .git/.graphite_cache_persist and returns branch relationship data
        along with current commit SHAs from git.

        Args:
            git_ops: GitOps instance for accessing git common directory and branch heads
            repo_root: Repository root directory

        Returns:
            Mapping of branch name -> BranchMetadata
            Empty dict if:
            - .graphite_cache_persist doesn't exist
            - Git common directory cannot be determined
        """
        ...

    @abstractmethod
    def get_branch_stack(self, git_ops: GitOps, repo_root: Path, branch: str) -> list[str] | None:
        """Get the linear graphite stack for a given branch.

        This function builds the linear chain of branches that the given branch belongs to.
        The chain includes:
        - All ancestor branches from current up to trunk
        - All descendant branches from current down to the leaf

        Args:
            git_ops: GitOps instance for accessing git common directory and branch heads
            repo_root: Repository root directory
            branch: Name of the branch to get the stack for

        Returns:
            List of branch names in the stack, ordered from trunk to leaf
            (e.g., ["main", "feature-1", "feature-2", "feature-3"]).
            Returns None if branch is not tracked by graphite
        """
        ...

    def get_parent_branch(self, git_ops: GitOps, repo_root: Path, branch: str) -> str | None:
        """Get parent branch name for a given branch.

        This is a convenience helper that calls get_all_branches() and extracts
        the parent relationship. All implementations inherit this method.

        Args:
            git_ops: GitOps instance for accessing git common directory
            repo_root: Repository root directory
            branch: Name of the branch to get the parent for

        Returns:
            Parent branch name, or None if:
            - Branch is not tracked by graphite
            - Branch has no parent (is trunk)
        """
        all_branches = self.get_all_branches(git_ops, repo_root)
        if branch not in all_branches:
            return None
        return all_branches[branch].parent

    def get_child_branches(self, git_ops: GitOps, repo_root: Path, branch: str) -> list[str]:
        """Get child branch names for a given branch.

        This is a convenience helper that calls get_all_branches() and extracts
        the children relationship. All implementations inherit this method.

        Args:
            git_ops: GitOps instance for accessing git common directory
            repo_root: Repository root directory
            branch: Name of the branch to get children for

        Returns:
            List of child branch names, or empty list if:
            - Branch is not tracked by graphite
            - Branch has no children
        """
        all_branches = self.get_all_branches(git_ops, repo_root)
        if branch not in all_branches:
            return []
        return all_branches[branch].children


class RealGraphiteOps(GraphiteOps):
    """Production implementation using gt CLI.

    All Graphite operations execute actual gt commands via subprocess.
    """

    def __init__(self) -> None:
        """Initialize with empty cache for get_all_branches."""
        self._branches_cache: dict[str, BranchMetadata] | None = None

    def get_graphite_url(self, owner: str, repo: str, pr_number: int) -> str:
        """Get Graphite PR URL for a pull request.

        Constructs the Graphite URL directly from GitHub repo information.
        No subprocess calls or external dependencies required.

        Args:
            owner: GitHub repository owner (e.g., "dagster-io")
            repo: GitHub repository name (e.g., "workstack")
            pr_number: GitHub PR number

        Returns:
            Graphite PR URL (e.g., "https://app.graphite.dev/github/pr/dagster-io/workstack/23")
        """
        return f"https://app.graphite.dev/github/pr/{owner}/{repo}/{pr_number}"

    def sync(self, repo_root: Path, *, force: bool, quiet: bool) -> None:
        """Run gt sync to synchronize with remote.

        Output goes directly to sys.stdout/sys.stderr to avoid capture by
        CliRunner when running in shell integration mode. This ensures gt sync
        output doesn't leak into the shell script that gets eval'd.

        Note: Uses try/except as an acceptable error boundary for handling gt CLI
        availability. We cannot reliably check gt installation status a priori.

        Args:
            repo_root: Repository root directory
            force: If True, pass --force flag to gt sync
            quiet: If True, pass --quiet flag to gt sync for minimal output
        """
        cmd = ["gt", "sync"]
        if force:
            cmd.append("-f")
        if quiet:
            cmd.append("--quiet")

        subprocess.run(
            cmd,
            cwd=repo_root,
            check=True,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

    def get_prs_from_graphite(self, git_ops: GitOps, repo_root: Path) -> dict[str, PullRequestInfo]:
        """Get PR information from Graphite's .git/.graphite_pr_info file."""
        git_dir = git_ops.get_git_common_dir(repo_root)
        if git_dir is None:
            return {}

        pr_info_file = git_dir / ".graphite_pr_info"
        if not pr_info_file.exists():
            return {}

        data = read_graphite_json_file(pr_info_file, "Graphite PR info")

        # parse_graphite_pr_info expects JSON string, so convert back
        return parse_graphite_pr_info(json.dumps(data))

    def get_all_branches(self, git_ops: GitOps, repo_root: Path) -> dict[str, BranchMetadata]:
        """Get all gt-tracked branches with metadata.

        Reads .git/.graphite_cache_persist and enriches with commit SHAs from git.
        Returns empty dict if cache doesn't exist or git operations fail.

        Results are cached for the lifetime of this instance to avoid redundant
        file reads and git subprocess calls.
        """
        # Return cached result if available
        if self._branches_cache is not None:
            return self._branches_cache

        git_dir = git_ops.get_git_common_dir(repo_root)
        if git_dir is None:
            self._branches_cache = {}
            return self._branches_cache

        cache_file = git_dir / ".graphite_cache_persist"
        if not cache_file.exists():
            self._branches_cache = {}
            return self._branches_cache

        data = read_graphite_json_file(cache_file, "Graphite cache")

        # Get all branch heads from git for enrichment
        git_branch_heads = {}
        branches_data = data.get("branches", [])
        for branch_name, _ in branches_data:
            if isinstance(branch_name, str):
                commit_sha = git_ops.get_branch_head(repo_root, branch_name)
                if commit_sha:
                    git_branch_heads[branch_name] = commit_sha

        # parse_graphite_cache expects JSON string, so convert back
        self._branches_cache = parse_graphite_cache(json.dumps(data), git_branch_heads)
        return self._branches_cache

    def get_branch_stack(self, git_ops: GitOps, repo_root: Path, branch: str) -> list[str] | None:
        """Get the linear graphite stack for a given branch."""
        # Get all branch metadata
        all_branches = self.get_all_branches(git_ops, repo_root)
        if not all_branches:
            return None

        # Check if the requested branch exists
        if branch not in all_branches:
            return None

        # Build parent-child map for traversal
        branch_info: dict[str, dict[str, str | list[str] | None]] = {}
        for name, metadata in all_branches.items():
            branch_info[name] = {
                "parent": metadata.parent,
                "children": metadata.children,
            }

        # Traverse DOWN to collect ancestors (current → parent → ... → trunk)
        ancestors: list[str] = []
        current = branch
        while current in branch_info:
            ancestors.append(current)
            parent = branch_info[current]["parent"]
            if parent is None or parent not in branch_info:
                break
            current = parent

        # Reverse to get [trunk, ..., parent, current]
        ancestors.reverse()

        # Traverse UP to collect descendants (current → child → ... → leaf)
        descendants: list[str] = []
        current = branch
        while True:
            children = branch_info[current]["children"]
            if not children:
                break
            # Follow the first child for linear stack
            first_child = children[0]
            if first_child not in branch_info:
                break
            descendants.append(first_child)
            current = first_child

        # Combine ancestors and descendants
        # ancestors already contains the current branch
        return ancestors + descendants


class DryRunGraphiteOps(GraphiteOps):
    """Wrapper that prints dry-run messages instead of executing destructive operations.

    This wrapper intercepts destructive graphite operations and prints what would happen
    instead of executing. Read-only operations are delegated to the wrapped implementation.

    Usage:
        real_ops = RealGraphiteOps()
        dry_run_ops = DryRunGraphiteOps(real_ops)

        # Prints message instead of running gt sync
        dry_run_ops.sync(repo_root, force=False)
    """

    def __init__(self, wrapped: GraphiteOps) -> None:
        """Create a dry-run wrapper around a GraphiteOps implementation.

        Args:
            wrapped: The GraphiteOps implementation to wrap (usually RealGraphiteOps)
        """
        self._wrapped = wrapped

    # Read-only operations: delegate to wrapped implementation

    def get_graphite_url(self, owner: str, repo: str, pr_number: int) -> str:
        """Get Graphite PR URL (read-only, delegates to wrapped)."""
        return self._wrapped.get_graphite_url(owner, repo, pr_number)

    def get_prs_from_graphite(self, git_ops: GitOps, repo_root: Path) -> dict[str, PullRequestInfo]:
        """Get PR info from Graphite cache (read-only, delegates to wrapped)."""
        return self._wrapped.get_prs_from_graphite(git_ops, repo_root)

    def get_all_branches(self, git_ops: GitOps, repo_root: Path) -> dict[str, BranchMetadata]:
        """Get all branches metadata (read-only, delegates to wrapped)."""
        return self._wrapped.get_all_branches(git_ops, repo_root)

    def get_branch_stack(self, git_ops: GitOps, repo_root: Path, branch: str) -> list[str] | None:
        """Get branch stack (read-only operation, delegates to wrapped)."""
        return self._wrapped.get_branch_stack(git_ops, repo_root, branch)

    # Destructive operations: print dry-run message instead of executing

    def sync(self, repo_root: Path, *, force: bool, quiet: bool) -> None:
        """Print dry-run message instead of running gt sync."""
        import click

        cmd = ["gt", "sync"]
        if force:
            cmd.append("-f")
        if quiet:
            cmd.append("--quiet")

        click.echo(f"[DRY RUN] Would run: {' '.join(cmd)}")
