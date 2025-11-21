"""Production implementation of GitHub operations."""

import json
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any

from erk.cli.output import user_output
from erk.core.github.abc import GitHub
from erk.core.github.parsing import (
    _determine_checks_status,
    execute_gh_command,
    parse_github_pr_list,
    parse_github_pr_status,
)
from erk.core.github.types import PRInfo, PRMergeability, PullRequestInfo
from erk.core.subprocess import run_subprocess_with_context


class RealGitHub(GitHub):
    """Production implementation using gh CLI.

    All GitHub operations execute actual gh commands via subprocess.
    """

    def __init__(self, execute_fn=None):
        """Initialize RealGitHub with optional command executor.

        Args:
            execute_fn: Optional function to execute commands (for testing).
                       If None, uses execute_gh_command.
        """
        self._execute = execute_fn or execute_gh_command

    def get_prs_for_repo(
        self, repo_root: Path, *, include_checks: bool
    ) -> dict[str, PullRequestInfo]:
        """Get PR information for all branches in the repository.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        try:
            # Build JSON fields list - conditionally include statusCheckRollup for performance
            json_fields = "number,headRefName,url,state,isDraft,title"
            if include_checks:
                json_fields += ",statusCheckRollup"

            cmd = [
                "gh",
                "pr",
                "list",
                "--state",
                "all",
                "--json",
                json_fields,
            ]
            stdout = self._execute(cmd, repo_root)
            return parse_github_pr_list(stdout, include_checks)

        except (RuntimeError, FileNotFoundError, json.JSONDecodeError):
            # gh not installed, not authenticated, or JSON parsing failed
            return {}

    def get_pr_status(self, repo_root: Path, branch: str, *, debug: bool) -> PRInfo:
        """Get PR status for a specific branch.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        try:
            # Query gh for PR info for this specific branch
            cmd = [
                "gh",
                "pr",
                "list",
                "--head",
                branch,
                "--state",
                "all",
                "--json",
                "number,state,title",
                "--limit",
                "1",
            ]

            if debug:
                user_output(f"$ {' '.join(cmd)}")

            stdout = self._execute(cmd, repo_root)
            return parse_github_pr_status(stdout)

        except (RuntimeError, FileNotFoundError, json.JSONDecodeError):
            # gh not installed, not authenticated, or JSON parsing failed
            return PRInfo("NONE", None, None)

    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str | None:
        """Get current base branch of a PR from GitHub.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        try:
            cmd = [
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--json",
                "baseRefName",
                "--jq",
                ".baseRefName",
            ]
            stdout = self._execute(cmd, repo_root)
            return stdout.strip()

        except (RuntimeError, FileNotFoundError):
            # gh not installed, not authenticated, or command failed
            return None

    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """Update base branch of a PR on GitHub.

        Gracefully handles gh CLI availability issues (not installed, not authenticated).
        The calling code should validate preconditions (PR exists, is open, new base exists)
        before calling this method.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability. Genuine command failures (invalid PR, invalid base) should be
        caught by precondition checks in the caller.
        """
        try:
            cmd = ["gh", "pr", "edit", str(pr_number), "--base", new_base]
            self._execute(cmd, repo_root)
        except (RuntimeError, FileNotFoundError):
            # gh not installed, not authenticated, or command failed
            # Graceful degradation - operation skipped
            # Caller is responsible for precondition validation
            pass

    def get_pr_mergeability(self, repo_root: Path, pr_number: int) -> PRMergeability | None:
        """Get PR mergeability status from GitHub via gh CLI.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        try:
            result = run_subprocess_with_context(
                ["gh", "pr", "view", str(pr_number), "--json", "mergeable,mergeStateStatus"],
                operation_context=f"check PR mergeability for PR #{pr_number}",
                cwd=repo_root,
            )
            data = json.loads(result.stdout)
            return PRMergeability(
                mergeable=data["mergeable"],
                merge_state_status=data["mergeStateStatus"],
            )
        except (
            RuntimeError,
            json.JSONDecodeError,
            KeyError,
            FileNotFoundError,
        ):
            return None

    def _build_batch_pr_query(self, pr_numbers: list[int], owner: str, repo: str) -> str:
        """Build GraphQL query with aliases for multiple PRs using named fragments.

        Args:
            pr_numbers: List of PR numbers to query
            owner: Repository owner
            repo: Repository name

        Returns:
            GraphQL query string
        """
        # Define the fragment once at the top of the query
        fragment_definition = """fragment PRCICheckFields on PullRequest {
  number
  mergeable
  mergeStateStatus
  commits(last: 1) {
    nodes {
      commit {
        statusCheckRollup {
          state
          contexts(last: 100) {
            nodes {
              ... on StatusContext {
                state
              }
              ... on CheckRun {
                status
                conclusion
              }
            }
          }
        }
      }
    }
  }
}"""

        # Build aliased PR queries using the fragment spread
        pr_queries = []
        for pr_num in pr_numbers:
            pr_query = f"""    pr_{pr_num}: pullRequest(number: {pr_num}) {{
      ...PRCICheckFields
    }}"""
            pr_queries.append(pr_query)

        # Combine fragment definition and query
        query = f"""{fragment_definition}

query {{
  repository(owner: "{owner}", name: "{repo}") {{
{chr(10).join(pr_queries)}
  }}
}}"""
        return query

    def _execute_batch_pr_query(self, query: str, repo_root: Path) -> dict[str, Any]:
        """Execute batched GraphQL query via gh CLI.

        Args:
            query: GraphQL query string
            repo_root: Repository root directory

        Returns:
            Parsed JSON response
        """
        cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
        stdout = self._execute(cmd, repo_root)
        return json.loads(stdout)

    def _parse_pr_ci_status(self, pr_data: dict[str, Any] | None) -> bool | None:
        """Parse CI status from GraphQL PR response.

        Args:
            pr_data: GraphQL response data for single PR (may be None)

        Returns:
            True if all checks passing, False if any failing, None if no checks or error
        """
        # Check if PR data is missing (not found or error)
        if pr_data is None:
            return None

        # Extract commits
        commits = pr_data.get("commits")
        if commits is None:
            return None

        # Check for empty commits nodes
        nodes = commits.get("nodes", [])
        if not nodes:
            return None

        # Extract statusCheckRollup from first commit
        commit = nodes[0].get("commit")
        if commit is None:
            return None

        status_check_rollup = commit.get("statusCheckRollup")
        if status_check_rollup is None:
            return None

        # Extract contexts connection
        contexts = status_check_rollup.get("contexts")
        if contexts is None:
            return None

        # Validate contexts is a dict (connection object) not a list
        # This handles cases where query structure is wrong or API changes
        if not isinstance(contexts, dict):
            return None

        # Extract nodes array from contexts connection
        nodes = contexts.get("nodes", [])

        # Call existing logic to determine status
        return _determine_checks_status(nodes)

    def _parse_pr_mergeability(self, pr_data: dict[str, Any] | None) -> bool | None:
        """Parse mergeability status from GraphQL PR data.

        Args:
            pr_data: PR data from GraphQL response (may be None for missing PRs)

        Returns:
            True if PR has conflicts, False if mergeable, None if unknown/unavailable
        """
        if pr_data is None:
            return None

        if "mergeable" not in pr_data:
            return None

        mergeable = pr_data["mergeable"]

        # Convert GitHub's mergeable status to has_conflicts boolean
        if mergeable == "CONFLICTING":
            return True
        if mergeable == "MERGEABLE":
            return False

        # UNKNOWN or other states
        return None

    def enrich_prs_with_ci_status_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Enrich PR information with CI check status and mergeability using batched GraphQL query.

        Fetches both CI status and mergeability for all PRs in a single GraphQL API call,
        dramatically improving performance over serial fetching.
        """
        # Early exit for empty input
        if not prs:
            return {}

        # Extract PR numbers and owner/repo from first PR
        pr_numbers = [pr.number for pr in prs.values()]
        first_pr = next(iter(prs.values()))
        owner = first_pr.owner
        repo = first_pr.repo

        # Build and execute batched GraphQL query
        query = self._build_batch_pr_query(pr_numbers, owner, repo)
        response = self._execute_batch_pr_query(query, repo_root)

        # Extract repository data from response
        repo_data = response["data"]["repository"]

        # Enrich each PR with CI status and mergeability
        enriched_prs = {}
        for branch, pr in prs.items():
            # Get PR data from GraphQL response using alias
            alias = f"pr_{pr.number}"
            pr_data = repo_data.get(alias)

            # Parse CI status (handles None/missing data gracefully)
            ci_status = self._parse_pr_ci_status(pr_data)

            # Parse mergeability status
            has_conflicts = self._parse_pr_mergeability(pr_data)

            # Create enriched PR with updated CI status and mergeability
            enriched_pr = replace(pr, checks_passing=ci_status, has_conflicts=has_conflicts)
            enriched_prs[branch] = enriched_pr

        return enriched_prs

    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
    ) -> None:
        """Merge a pull request on GitHub via gh CLI."""
        cmd = ["gh", "pr", "merge", str(pr_number)]
        if squash:
            cmd.append("--squash")

        result = run_subprocess_with_context(
            cmd,
            operation_context=f"merge PR #{pr_number}",
            cwd=repo_root,
        )

        # Show output in verbose mode
        if verbose and result.stdout:
            user_output(result.stdout)

    def trigger_workflow(
        self,
        repo_root: Path,
        workflow: str,
        inputs: dict[str, str],
        ref: str | None = None,
    ) -> str:
        """Trigger GitHub Actions workflow via gh CLI.

        Args:
            repo_root: Repository root path
            workflow: Workflow file name (e.g., "implement-plan.yml")
            inputs: Workflow inputs as key-value pairs
            ref: Branch or tag to run workflow from (default: repository default branch)

        Returns:
            The GitHub Actions run ID as a string
        """
        cmd = ["gh", "workflow", "run", workflow, "--json"]

        # Add --ref flag if specified
        if ref:
            cmd.extend(["--ref", ref])

        # Add workflow inputs
        for key, value in inputs.items():
            cmd.extend(["-f", f"{key}={value}"])

        result = run_subprocess_with_context(
            cmd,
            operation_context=f"trigger workflow '{workflow}'",
            cwd=repo_root,
        )

        # Parse JSON output to extract run ID
        data = json.loads(result.stdout)
        if "id" not in data:
            msg = (
                "GitHub workflow triggered but run ID not found in response. "
                f"Raw output: {result.stdout[:200]}"
            )
            raise RuntimeError(msg)

        run_id = data["id"]
        return str(run_id)
