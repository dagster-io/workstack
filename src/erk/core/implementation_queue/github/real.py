"""Production implementation of GitHub Actions admin operations."""

import json
from pathlib import Path
from typing import Any

from erk.core.implementation_queue.github.abc import GitHubAdmin
from erk.core.subprocess import run_subprocess_with_context


class RealGitHubAdmin(GitHubAdmin):
    """Production implementation using gh CLI.

    All GitHub Actions admin operations execute actual gh commands via subprocess.
    """

    def _extract_owner_repo(self, repo_root: Path) -> tuple[str, str]:
        """Extract owner and repo name from git remote.

        Args:
            repo_root: Repository root directory

        Returns:
            Tuple of (owner, repo) strings

        Raises:
            RuntimeError: If unable to determine owner/repo from remote
        """
        result = run_subprocess_with_context(
            ["gh", "repo", "view", "--json", "owner,name"],
            operation_context="extract repository owner and name",
            cwd=repo_root,
        )
        data = json.loads(result.stdout)
        owner = data["owner"]["login"]
        repo = data["name"]
        return owner, repo

    def get_workflow_permissions(self, repo_root: Path) -> dict[str, Any]:
        """Get current workflow permissions using gh CLI.

        Args:
            repo_root: Repository root directory

        Returns:
            Dict with keys:
            - default_workflow_permissions: "read" or "write"
            - can_approve_pull_request_reviews: bool

        Raises:
            RuntimeError: If gh CLI command fails
        """
        owner, repo = self._extract_owner_repo(repo_root)

        cmd = [
            "gh",
            "api",
            "-H",
            "Accept: application/vnd.github+json",
            "-H",
            "X-GitHub-Api-Version: 2022-11-28",
            f"/repos/{owner}/{repo}/actions/permissions/workflow",
        ]

        result = run_subprocess_with_context(
            cmd,
            operation_context=f"get workflow permissions for {owner}/{repo}",
            cwd=repo_root,
        )

        return json.loads(result.stdout)

    def set_workflow_pr_permissions(self, repo_root: Path, enabled: bool) -> None:
        """Enable/disable PR creation via workflow permissions API.

        Args:
            repo_root: Repository root directory
            enabled: True to enable PR creation, False to disable

        Raises:
            RuntimeError: If gh CLI command fails
        """
        owner, repo = self._extract_owner_repo(repo_root)

        # CRITICAL: Must set both fields together
        # - default_workflow_permissions: Keep as "read" (workflows declare their own)
        # - can_approve_pull_request_reviews: This enables PR creation
        cmd = [
            "gh",
            "api",
            "--method",
            "PUT",
            "-H",
            "Accept: application/vnd.github+json",
            "-H",
            "X-GitHub-Api-Version: 2022-11-28",
            f"/repos/{owner}/{repo}/actions/permissions/workflow",
            "-f",
            "default_workflow_permissions=read",
            "-F",
            f"can_approve_pull_request_reviews={str(enabled).lower()}",
        ]

        run_subprocess_with_context(
            cmd,
            operation_context=f"set workflow PR permissions for {owner}/{repo}",
            cwd=repo_root,
        )
