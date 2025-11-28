"""Real GitHub implementation using gh CLI.

This module provides a real implementation of the GitHub interface that uses
the gh CLI for all operations. This is the production implementation used
by both erk and dot-agent-kit.
"""

import json
import subprocess
from pathlib import Path
from typing import cast

from erk_shared.github.abc import GitHub
from erk_shared.github.parsing import parse_gh_auth_status_output
from erk_shared.github.types import (
    PRCheckoutInfo,
    PRInfo,
    PRMergeability,
    PRState,
    PullRequestInfo,
    WorkflowRun,
)


def _run_subprocess_with_timeout(
    cmd: list[str],
    timeout: int = 30,
    capture_output: bool = True,
    text: bool = True,
    check: bool = False,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str] | None:
    """Run subprocess with timeout, returning None on timeout."""
    try:
        return subprocess.run(
            cmd,
            timeout=timeout,
            capture_output=capture_output,
            text=text,
            check=check,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        return None


class RealGitHub(GitHub):
    """Real implementation using gh CLI.

    This implementation calls the gh CLI for all GitHub operations.
    It requires the gh CLI to be installed and authenticated.
    """

    def __init__(self) -> None:
        """Initialize RealGitHub."""

    def get_prs_for_repo(
        self, repo_root: Path, *, include_checks: bool
    ) -> dict[str, PullRequestInfo]:
        """Get PRs for all branches in the repository."""
        json_fields = "number,state,url,headRefName,title,isDraft"
        result = _run_subprocess_with_timeout(
            ["gh", "pr", "list", "--state", "all", "--json", json_fields],
            timeout=30,
            cwd=repo_root,
        )

        if result is None or result.returncode != 0:
            return {}

        prs: dict[str, PullRequestInfo] = {}
        try:
            data = json.loads(result.stdout)
            for pr in data:
                branch = pr["headRefName"]
                prs[branch] = PullRequestInfo(
                    number=pr["number"],
                    state=pr["state"],
                    url=pr["url"],
                    is_draft=pr.get("isDraft", False),
                    title=pr.get("title"),
                    checks_passing=None,
                    owner="",
                    repo="",
                    has_conflicts=None,
                )
        except (json.JSONDecodeError, KeyError):
            pass

        return prs

    def get_pr_status(self, repo_root: Path, branch: str, *, debug: bool) -> PRInfo:
        """Get PR status for a specific branch."""
        result = _run_subprocess_with_timeout(
            ["gh", "pr", "list", "--head", branch, "--json", "number,state,title"],
            timeout=10,
            cwd=repo_root,
        )

        if result is None or result.returncode != 0:
            return PRInfo("NONE", None, None)

        try:
            data = json.loads(result.stdout)
            if not data:
                return PRInfo("NONE", None, None)
            pr = data[0]
            return PRInfo(
                cast(PRState, pr["state"]),
                pr["number"],
                pr.get("title"),
            )
        except (json.JSONDecodeError, KeyError):
            return PRInfo("NONE", None, None)

    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str | None:
        """Get base branch for a PR."""
        result = _run_subprocess_with_timeout(
            ["gh", "pr", "view", str(pr_number), "--json", "baseRefName"],
            timeout=10,
            cwd=repo_root,
        )

        if result is None or result.returncode != 0:
            return None

        try:
            data = json.loads(result.stdout)
            return data.get("baseRefName")
        except json.JSONDecodeError:
            return None

    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """Update the base branch of a PR."""
        subprocess.run(
            ["gh", "pr", "edit", str(pr_number), "--base", new_base],
            check=True,
            cwd=repo_root,
            capture_output=True,
        )

    def get_pr_mergeability(self, repo_root: Path, pr_number: int) -> PRMergeability | None:
        """Get PR mergeability status."""
        result = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{{owner}}/{{repo}}/pulls/{pr_number}",
                "--jq",
                ".mergeable,.mergeable_state",
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=repo_root,
        )

        if result.returncode != 0:
            return None

        lines = result.stdout.strip().split("\n")
        mergeable_str = lines[0] if len(lines) > 0 else "null"
        merge_state = lines[1] if len(lines) > 1 else "unknown"

        # Convert to GitHub GraphQL enum format
        if mergeable_str == "true":
            return PRMergeability(mergeable="MERGEABLE", merge_state_status=merge_state.upper())
        if mergeable_str == "false":
            return PRMergeability(mergeable="CONFLICTING", merge_state_status=merge_state.upper())
        return PRMergeability(mergeable="UNKNOWN", merge_state_status="UNKNOWN")

    def enrich_prs_with_ci_status_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Enrich PRs with CI status - minimal implementation."""
        # This method is complex in the full erk implementation
        # For erk-shared, we return PRs unchanged
        return prs

    def fetch_pr_titles_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Fetch PR titles - minimal implementation."""
        return prs

    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
    ) -> None:
        """Merge a PR using gh CLI."""
        cmd = ["gh", "pr", "merge", str(pr_number)]
        if squash:
            cmd.append("--squash")
        else:
            cmd.append("--merge")

        subprocess.run(cmd, check=True, cwd=repo_root, capture_output=True)

    def trigger_workflow(
        self,
        repo_root: Path,
        workflow: str,
        inputs: dict[str, str],
        ref: str | None = None,
    ) -> str:
        """Trigger a workflow - stub for erk-shared."""
        msg = "trigger_workflow not implemented in erk-shared"
        raise NotImplementedError(msg)

    def create_pr(
        self,
        repo_root: Path,
        branch: str,
        title: str,
        body: str,
        base: str | None = None,
    ) -> int:
        """Create a PR using gh CLI."""
        cmd = ["gh", "pr", "create", "--head", branch, "--title", title, "--body", body]
        if base is not None:
            cmd.extend(["--base", base])

        result = subprocess.run(
            cmd,
            check=True,
            cwd=repo_root,
            capture_output=True,
            text=True,
        )

        # Parse PR URL to get number
        # URL format: https://github.com/owner/repo/pull/123
        url = result.stdout.strip()
        pr_number = int(url.split("/")[-1])
        return pr_number

    def list_workflow_runs(
        self, repo_root: Path, workflow: str, limit: int = 50
    ) -> list[WorkflowRun]:
        """List workflow runs - stub for erk-shared."""
        return []

    def get_workflow_run(self, repo_root: Path, run_id: str) -> WorkflowRun | None:
        """Get workflow run - stub for erk-shared."""
        return None

    def get_run_logs(self, repo_root: Path, run_id: str) -> str:
        """Get run logs - stub for erk-shared."""
        msg = "get_run_logs not implemented in erk-shared"
        raise NotImplementedError(msg)

    def get_prs_linked_to_issues(
        self, repo_root: Path, issue_numbers: list[int]
    ) -> dict[int, list[PullRequestInfo]]:
        """Get PRs linked to issues - stub for erk-shared."""
        return {}

    def get_workflow_runs_by_branches(
        self, repo_root: Path, workflow: str, branches: list[str]
    ) -> dict[str, WorkflowRun | None]:
        """Get workflow runs by branches - stub for erk-shared."""
        return {}

    def poll_for_workflow_run(
        self,
        repo_root: Path,
        workflow: str,
        branch_name: str,
        timeout: int = 30,
        poll_interval: int = 2,
    ) -> str | None:
        """Poll for workflow run - stub for erk-shared."""
        return None

    def get_pr_checkout_info(self, repo_root: Path, pr_number: int) -> PRCheckoutInfo | None:
        """Get PR checkout info - stub for erk-shared."""
        return None

    def get_workflow_runs_batch(
        self, repo_root: Path, run_ids: list[str]
    ) -> dict[str, WorkflowRun | None]:
        """Get workflow runs batch - stub for erk-shared."""
        return {}

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Check GitHub CLI authentication status."""
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return (False, None, None)

        output = result.stdout + result.stderr
        return parse_gh_auth_status_output(output)

    def update_pr_metadata(self, repo_root: Path, pr_number: int, title: str, body: str) -> bool:
        """Update PR title and body using gh pr edit."""
        result = _run_subprocess_with_timeout(
            ["gh", "pr", "edit", str(pr_number), "--title", title, "--body", body],
            timeout=30,
            cwd=repo_root,
        )

        if result is None:
            return False
        return result.returncode == 0

    def mark_pr_ready(self, repo_root: Path, pr_number: int) -> bool:
        """Mark PR as ready for review."""
        result = subprocess.run(
            ["gh", "pr", "ready", str(pr_number)],
            capture_output=True,
            text=True,
            check=False,
            cwd=repo_root,
        )
        return result.returncode == 0

    def get_graphite_pr_url(self, repo_root: Path, pr_number: int) -> str | None:
        """Get Graphite PR URL by querying repository info."""
        result = _run_subprocess_with_timeout(
            ["gh", "repo", "view", "--json", "owner,name"],
            timeout=10,
            cwd=repo_root,
        )

        if result is None or result.returncode != 0:
            return None

        try:
            data = json.loads(result.stdout)
            owner = data["owner"]["login"]
            repo = data["name"]
            return f"https://app.graphite.com/github/pr/{owner}/{repo}/{pr_number}"
        except (json.JSONDecodeError, KeyError):
            return None

    def get_pr_diff(self, repo_root: Path, pr_number: int) -> str:
        """Get the diff for a PR using gh pr diff."""
        result = subprocess.run(
            ["gh", "pr", "diff", str(pr_number)],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_root,
        )
        return result.stdout
