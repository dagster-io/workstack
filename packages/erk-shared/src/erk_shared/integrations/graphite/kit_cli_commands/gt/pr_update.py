"""Graphite update-pr workflow.

This module provides a streamlined version of the Graphite update-pr workflow.

Design goals:
- Fail fast with natural error messages
- Single linear execution flow
- No error categorization or state tracking
- Uses direct ABC injection instead of GtKit wrapper
- Simple JSON output without complex types
"""

import json
import sys
from pathlib import Path

import click

from erk_shared.git.abc import Git
from erk_shared.git.real import RealGit
from erk_shared.github.abc import GitHub
from erk_shared.github.real import RealGitHub
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.graphite.real import RealGraphite


def _get_pr_info(github: GitHub, repo_root: Path, branch: str) -> tuple[int, str] | None:
    """Get PR number and URL for a branch.

    Args:
        github: GitHub operations interface
        repo_root: Repository root directory
        branch: Branch name to look up

    Returns:
        Tuple of (pr_number, pr_url) or None if no PR exists
    """
    prs = github.get_prs_for_repo(repo_root, include_checks=False)
    if branch in prs:
        pr = prs[branch]
        return (pr.number, pr.url)
    return None


def execute_update_pr(
    git: Git | None = None,
    github: GitHub | None = None,
    graphite: Graphite | None = None,
    repo_root: Path | None = None,
) -> dict:
    """Execute the update-pr workflow.

    Args:
        git: Git operations interface. Defaults to RealGit().
        github: GitHub operations interface. Defaults to RealGitHub().
        graphite: Graphite operations interface. Defaults to RealGraphite().
        repo_root: Repository root directory. Defaults to cwd.

    Returns:
        JSON dict with:
        - success: bool
        - pr_number: int (if successful)
        - pr_url: str (if successful)
        - error: str (if failed)
    """
    if git is None:
        git = RealGit()
    if github is None:
        github = RealGitHub()
    if graphite is None:
        graphite = RealGraphite()
    if repo_root is None:
        repo_root = Path.cwd()

    # 1. Commit if uncommitted changes
    if git.has_uncommitted_changes(repo_root):
        if not git.add_all(repo_root):
            return {"success": False, "error": "Failed to stage changes"}
        if not git.commit(repo_root, "Update changes"):
            return {"success": False, "error": "Failed to commit changes"}

    # 2. Restack with conflict detection
    restack_result = graphite.restack_with_result(repo_root)
    if not restack_result.success:
        combined_output = restack_result.stdout + restack_result.stderr
        combined_lower = combined_output.lower()

        if "conflict" in combined_lower or "merge conflict" in combined_lower:
            return {
                "success": False,
                "error_type": "restack_conflict",
                "error": (
                    "Merge conflict detected during restack. "
                    "Resolve conflicts manually or run 'gt restack --continue' after fixing."
                ),
                "details": {"stderr": restack_result.stderr},
            }

        return {
            "success": False,
            "error_type": "restack_failed",
            "error": "Failed to restack branch",
            "details": {"stderr": restack_result.stderr},
        }

    # 3. Submit update
    result = graphite.submit(repo_root, publish=True, restack=False)
    if not result.success:
        return {"success": False, "error": f"Failed to submit update: {result.stderr}"}

    # 4. Fetch PR info after submission
    branch = git.get_current_branch(repo_root)
    if branch is None:
        return {"success": False, "error": "Could not determine current branch"}

    pr_info = _get_pr_info(github, repo_root, branch)
    if not pr_info:
        return {"success": False, "error": "PR submission succeeded but failed to retrieve PR info"}

    pr_number, pr_url = pr_info

    return {"success": True, "pr_number": pr_number, "pr_url": pr_url}


@click.command()
def pr_update() -> None:
    """Graphite update-pr workflow.

    Usage:
        dot-agent run gt pr-update
    """
    result = execute_update_pr()
    print(json.dumps(result))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    pr_update()
