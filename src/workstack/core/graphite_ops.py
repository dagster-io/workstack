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


def read_graphite_json_file(file_path: Path, description: str) -> dict[str, Any] | None:
    """Read and parse a Graphite JSON file with error handling.

    Args:
        file_path: Path to the JSON file
        description: Human-readable description for error messages
            (e.g., "Graphite cache", "Graphite PR info")

    Returns:
        Parsed JSON dict, or None if file doesn't exist or error occurs

    Note:
        Emits warnings for parse/read errors to inform user of cache issues
        without crashing the application.
    """
    if not file_path.exists():
        return None

    try:
        json_str = file_path.read_text(encoding="utf-8")
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        warnings.warn(
            f"Cannot parse {description} at {file_path}: Invalid JSON ({e})",
            stacklevel=2,
        )
        return None
    except OSError as e:
        warnings.warn(
            f"Cannot read {description} at {file_path}: {e}",
            stacklevel=2,
        )
        return None


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
    def sync(self, repo_root: Path, *, force: bool) -> None:
        """Run gt sync to synchronize with remote.

        Args:
            repo_root: Repository root directory
            force: If True, pass --force flag to gt sync
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


class RealGraphiteOps(GraphiteOps):
    """Production implementation using gt CLI.

    All Graphite operations execute actual gt commands via subprocess.
    """

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

    def sync(self, repo_root: Path, *, force: bool) -> None:
        """Run gt sync to synchronize with remote.

        Output goes directly to sys.stdout/sys.stderr to avoid capture by
        CliRunner when running in shell integration mode. This ensures gt sync
        output doesn't leak into the shell script that gets eval'd.

        Note: Uses try/except as an acceptable error boundary for handling gt CLI
        availability. We cannot reliably check gt installation status a priori.
        """
        cmd = ["gt", "sync"]
        if force:
            cmd.append("-f")

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
        data = read_graphite_json_file(pr_info_file, "Graphite PR info")
        if data is None:
            return {}

        # parse_graphite_pr_info expects JSON string, so convert back
        return parse_graphite_pr_info(json.dumps(data))

    def get_all_branches(self, git_ops: GitOps, repo_root: Path) -> dict[str, BranchMetadata]:
        """Get all gt-tracked branches with metadata.

        Reads .git/.graphite_cache_persist and enriches with commit SHAs from git.
        Returns empty dict if cache doesn't exist or git operations fail.
        """
        git_dir = git_ops.get_git_common_dir(repo_root)
        if git_dir is None:
            return {}

        cache_file = git_dir / ".graphite_cache_persist"
        data = read_graphite_json_file(cache_file, "Graphite cache")
        if data is None:
            return {}

        # Get all branch heads from git for enrichment
        git_branch_heads = {}
        branches_data = data.get("branches", [])
        for branch_name, _ in branches_data:
            if isinstance(branch_name, str):
                commit_sha = git_ops.get_branch_head(repo_root, branch_name)
                if commit_sha:
                    git_branch_heads[branch_name] = commit_sha

        # parse_graphite_cache expects JSON string, so convert back
        return parse_graphite_cache(json.dumps(data), git_branch_heads)


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

    # Destructive operations: print dry-run message instead of executing

    def sync(self, repo_root: Path, *, force: bool) -> None:
        """Print dry-run message instead of running gt sync."""
        import click

        cmd = ["gt", "sync"]
        if force:
            cmd.append("-f")

        click.echo(f"[DRY RUN] Would run: {' '.join(cmd)}")
