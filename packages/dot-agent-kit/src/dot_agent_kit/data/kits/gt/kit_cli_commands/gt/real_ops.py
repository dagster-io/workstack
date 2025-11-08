"""Real subprocess-based implementations of GT kit operations interfaces.

This module provides concrete implementations that wrap subprocess.run calls
for git, Graphite (gt), and GitHub (gh) commands. These are the production
implementations used by GT kit CLI commands.

Design:
- Each implementation wraps existing subprocess patterns from CLI commands
- Returns match interface contracts (str | None, bool, tuple)
- Uses check=False to allow LBYL error handling
- RealGtKitOps composes all three real implementations
"""

import json
import subprocess

from dot_agent_kit.data.kits.gt.kit_cli_commands.gt.ops import (
    GitGtKitOps,
    GitHubGtKitOps,
    GraphiteGtKitOps,
    GtKitOps,
)


class RealGitGtKitOps(GitGtKitOps):
    """Real git operations using subprocess."""

    def get_current_branch(self) -> str | None:
        """Get the name of the current branch using git."""
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return None

        return result.stdout.strip()

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes using git status."""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return False

        return len(result.stdout.strip()) > 0

    def add_all(self) -> bool:
        """Stage all changes using git add."""
        result = subprocess.run(
            ["git", "add", "."],
            capture_output=True,
            text=True,
            check=False,
        )

        return result.returncode == 0

    def commit(self, message: str) -> bool:
        """Create a commit using git commit."""
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True,
            text=True,
            check=False,
        )

        return result.returncode == 0

    def amend_commit(self, message: str) -> bool:
        """Amend the current commit using git commit --amend."""
        result = subprocess.run(
            ["git", "commit", "--amend", "-m", message],
            capture_output=True,
            text=True,
            check=False,
        )

        return result.returncode == 0

    def count_commits_in_branch(self, parent_branch: str) -> int:
        """Count commits in current branch using git rev-list."""
        result = subprocess.run(
            ["git", "rev-list", "--count", f"{parent_branch}..HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return 0

        count_str = result.stdout.strip()
        if not count_str:
            return 0

        return int(count_str)


class RealGraphiteGtKitOps(GraphiteGtKitOps):
    """Real Graphite operations using subprocess."""

    def get_parent_branch(self) -> str | None:
        """Get the parent branch using gt parent."""
        result = subprocess.run(
            ["gt", "parent"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return None

        return result.stdout.strip()

    def get_children_branches(self) -> list[str]:
        """Get list of child branches using gt children."""
        result = subprocess.run(
            ["gt", "children"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return []

        # gt children outputs one branch per line
        children = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        return children

    def squash_commits(self) -> bool:
        """Run gt squash to consolidate commits."""
        result = subprocess.run(
            ["gt", "squash"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0

    def submit(self, publish: bool = False, restack: bool = False) -> tuple[bool, str, str]:
        """Run gt submit to create or update PR."""
        args = ["gt", "submit", "--no-interactive"]

        if publish:
            args.append("--publish")

        if restack:
            args.append("--restack")

        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
        )

        return (result.returncode == 0, result.stdout, result.stderr)

    def restack(self) -> bool:
        """Run gt restack in no-interactive mode."""
        result = subprocess.run(
            ["gt", "restack", "--no-interactive"],
            capture_output=True,
            text=True,
            check=False,
        )

        return result.returncode == 0

    def navigate_to_child(self) -> bool:
        """Navigate to child branch using gt up."""
        result = subprocess.run(
            ["gt", "up"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0


class RealGitHubGtKitOps(GitHubGtKitOps):
    """Real GitHub operations using subprocess."""

    def get_pr_info(self) -> tuple[int, str] | None:
        """Get PR number and URL using gh pr view."""
        result = subprocess.run(
            ["gh", "pr", "view", "--json", "number,url"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        return (data["number"], data["url"])

    def get_pr_state(self) -> tuple[int, str] | None:
        """Get PR number and state using gh pr view."""
        result = subprocess.run(
            ["gh", "pr", "view", "--json", "state,number"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        return (data["number"], data["state"])

    def update_pr_metadata(self, title: str, body: str) -> bool:
        """Update PR title and body using gh pr edit."""
        result = subprocess.run(
            ["gh", "pr", "edit", "--title", title, "--body", body],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0

    def merge_pr(self) -> bool:
        """Merge the PR using squash merge with gh pr merge."""
        result = subprocess.run(
            ["gh", "pr", "merge", "-s"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0


class RealGtKitOps(GtKitOps):
    """Real composite operations implementation.

    Combines real git, Graphite, and GitHub operations for production use.
    """

    def __init__(self) -> None:
        """Initialize real operations instances."""
        self._git = RealGitGtKitOps()
        self._graphite = RealGraphiteGtKitOps()
        self._github = RealGitHubGtKitOps()

    def git(self) -> GitGtKitOps:
        """Get the git operations interface."""
        return self._git

    def graphite(self) -> GraphiteGtKitOps:
        """Get the Graphite operations interface."""
        return self._graphite

    def github(self) -> GitHubGtKitOps:
        """Get the GitHub operations interface."""
        return self._github
