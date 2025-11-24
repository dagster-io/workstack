"""Production implementation of Graphite operations."""

import json
import subprocess
import sys
from pathlib import Path
from subprocess import DEVNULL

from erk.cli.output import user_output
from erk.core.branch_metadata import BranchMetadata
from erk_shared.git.abc import Git
from erk_shared.github.types import PullRequestInfo
from erk.core.graphite.abc import Graphite
from erk.core.graphite.parsing import (
    parse_graphite_cache,
    parse_graphite_pr_info,
    read_graphite_json_file,
)
from erk.core.subprocess import run_subprocess_with_context


class RealGraphite(Graphite):
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
            repo: GitHub repository name (e.g., "erk")
            pr_number: GitHub PR number

        Returns:
            Graphite PR URL (e.g., "https://app.graphite.com/github/pr/dagster-io/erk/23")
        """
        return f"https://app.graphite.com/github/pr/{owner}/{repo}/{pr_number}"

    def sync(self, repo_root: Path, *, force: bool, quiet: bool) -> None:
        """Run gt sync to synchronize with remote.

        Error output (stderr) is always captured to ensure RuntimeError
        includes complete error messages for debugging. In verbose mode (!quiet),
        stderr is displayed to the user after successful execution.

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

        result = run_subprocess_with_context(
            cmd,
            operation_context="sync with Graphite (gt sync)",
            cwd=repo_root,
            stdout=DEVNULL if quiet else sys.stdout,
            stderr=subprocess.PIPE,
        )

        # Display stderr in verbose mode after successful execution
        if not quiet and result.stderr:
            user_output(result.stderr, nl=False)

        # Invalidate branches cache - gt sync modifies Graphite metadata
        self._branches_cache = None

    def restack(self, repo_root: Path, *, no_interactive: bool, quiet: bool) -> None:
        """Run gt restack to rebase the current stack.

        More surgical than sync - only affects the current stack, not all branches
        in the repository. Safe to use with --no-interactive in automated workflows.

        Error output (stderr) is always captured to ensure RuntimeError
        includes complete error messages for debugging. In verbose mode (!quiet),
        stderr is displayed to the user after successful execution.

        Args:
            repo_root: Repository root directory
            no_interactive: If True, pass --no-interactive flag to prevent prompts
            quiet: If True, pass --quiet flag to gt restack for minimal output
        """
        cmd = ["gt", "restack"]
        if no_interactive:
            cmd.append("--no-interactive")
        if quiet:
            cmd.append("--quiet")

        result = run_subprocess_with_context(
            cmd,
            operation_context="restack with Graphite (gt restack)",
            cwd=repo_root,
            stdout=DEVNULL if quiet else sys.stdout,
            stderr=subprocess.PIPE,
        )

        # Display stderr in verbose mode after successful execution
        if not quiet and result.stderr:
            user_output(result.stderr, nl=False)

        # Invalidate branches cache - gt restack modifies Graphite metadata
        self._branches_cache = None

    def get_prs_from_graphite(self, git_ops: Git, repo_root: Path) -> dict[str, PullRequestInfo]:
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

    def get_all_branches(self, git_ops: Git, repo_root: Path) -> dict[str, BranchMetadata]:
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

    def get_branch_stack(self, git_ops: Git, repo_root: Path, branch: str) -> list[str] | None:
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

    def track_branch(self, cwd: Path, branch_name: str, parent_branch: str) -> None:
        """Track a branch with Graphite.

        Uses `gt track --branch <branch> --parent <parent>` to register a branch
        in Graphite's cache. This is needed when branches are created with direct
        git operations (git branch) instead of gt create.

        Args:
            cwd: Working directory where gt track should run
            branch_name: Name of the branch to track
            parent_branch: Name of the parent branch in the stack
        """
        run_subprocess_with_context(
            ["gt", "track", "--branch", branch_name, "--parent", parent_branch],
            operation_context=f"track branch '{branch_name}' with Graphite",
            cwd=cwd,
        )

        # Invalidate branches cache - gt track modifies Graphite metadata
        self._branches_cache = None

    def submit_branch(self, repo_root: Path, branch_name: str, *, quiet: bool) -> None:
        """Submit (force-push) a branch to GitHub.

        Uses `gt submit --branch <branch> --no-edit` to push a branch that was
        rebased by `gt sync -f`. This ensures GitHub PRs show the rebased commits
        rather than stale versions with duplicate commits.

        Error output (stderr) is always captured to ensure RuntimeError
        includes complete error messages for debugging. In verbose mode (!quiet),
        stderr is displayed to the user after successful execution.

        Args:
            repo_root: Repository root directory
            branch_name: Name of the branch to submit
            quiet: If True, pass --quiet flag to gt submit for minimal output
        """
        cmd = ["gt", "submit", "--branch", branch_name, "--no-edit"]
        if quiet:
            cmd.append("--quiet")

        result = run_subprocess_with_context(
            cmd,
            operation_context=f"submit branch '{branch_name}' with Graphite",
            cwd=repo_root,
            stdout=DEVNULL if quiet else sys.stdout,
            stderr=subprocess.PIPE,
        )

        # Display stderr in verbose mode after successful execution
        if not quiet and result.stderr:
            user_output(result.stderr, nl=False)
