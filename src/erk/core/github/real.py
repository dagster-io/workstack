"""Production implementation of GitHub operations."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from erk_shared.github.abc import GitHub
from erk_shared.github.types import PRInfo, PRMergeability, PullRequestInfo, WorkflowRun
from erk_shared.subprocess_utils import run_subprocess_with_context

from erk.cli.output import user_output
from erk.core.github.parsing import (
    _determine_checks_status,
    execute_gh_command,
    parse_github_pr_list,
    parse_github_pr_status,
)
from erk.core.time.abc import Time


class RealGitHub(GitHub):
    """Production implementation using gh CLI.

    All GitHub operations execute actual gh commands via subprocess.
    """

    def __init__(self, time: Time):
        """Initialize RealGitHub.

        Args:
            time: Time abstraction for sleep operations
        """
        self._time = time

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
            stdout = execute_gh_command(cmd, repo_root)
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

            stdout = execute_gh_command(cmd, repo_root)
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
            stdout = execute_gh_command(cmd, repo_root)
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
            execute_gh_command(cmd, repo_root)
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
  title
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
        stdout = execute_gh_command(cmd, repo_root)
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

            # Extract title from PR data
            title = pr_data.get("title") if pr_data else None

            # Create enriched PR with updated CI status, mergeability, and title
            enriched_pr = replace(
                pr, checks_passing=ci_status, has_conflicts=has_conflicts, title=title
            )
            enriched_prs[branch] = enriched_pr

        return enriched_prs

    def fetch_pr_titles_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Fetch PR titles for all PRs in a single batched GraphQL query.

        This is a lighter-weight alternative to enrich_prs_with_ci_status_batch
        that only fetches titles, not CI status or mergeability.

        Args:
            prs: Dictionary mapping branch names to PullRequestInfo objects
            repo_root: Repository root path

        Returns:
            Dictionary with same keys, but PullRequestInfo objects enriched with titles
        """
        # Early exit for empty input
        if not prs:
            return {}

        # Extract PR numbers and owner/repo from first PR
        pr_numbers = [pr.number for pr in prs.values()]
        first_pr = next(iter(prs.values()))
        owner = first_pr.owner
        repo = first_pr.repo

        # Build simplified GraphQL query for just titles
        query = self._build_title_batch_query(pr_numbers, owner, repo)
        response = self._execute_batch_pr_query(query, repo_root)

        # Extract repository data from response
        repo_data = response["data"]["repository"]

        # Enrich each PR with title
        enriched_prs = {}
        for branch, pr in prs.items():
            # Get PR data from GraphQL response using alias
            alias = f"pr_{pr.number}"
            pr_data = repo_data.get(alias)

            # Extract title from PR data
            title = pr_data.get("title") if pr_data else None

            # Create enriched PR with title
            enriched_pr = replace(pr, title=title)
            enriched_prs[branch] = enriched_pr

        return enriched_prs

    def _build_title_batch_query(self, pr_numbers: list[int], owner: str, repo: str) -> str:
        """Build GraphQL query to fetch just titles for multiple PRs.

        Args:
            pr_numbers: List of PR numbers to query
            owner: Repository owner
            repo: Repository name

        Returns:
            GraphQL query string
        """
        # Build aliased PR queries for titles only
        pr_queries = []
        for pr_num in pr_numbers:
            pr_query = f"""    pr_{pr_num}: pullRequest(number: {pr_num}) {{
      number
      title
    }}"""
            pr_queries.append(pr_query)

        # Combine into single query
        query = f"""query {{
  repository(owner: "{owner}", name: "{repo}") {{
{chr(10).join(pr_queries)}
  }}
}}"""
        return query

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
        cmd = ["gh", "workflow", "run", workflow]

        # Add --ref flag if specified
        if ref:
            cmd.extend(["--ref", ref])

        # Add workflow inputs
        for key, value in inputs.items():
            cmd.extend(["-f", f"{key}={value}"])

        # Record trigger time right before calling gh workflow run
        trigger_time = datetime.now(UTC)

        run_subprocess_with_context(
            cmd,
            operation_context=f"trigger workflow '{workflow}'",
            cwd=repo_root,
        )

        # The gh workflow run command doesn't return JSON output by default
        # We need to get the run ID from the workflow runs list
        # Retry logic handles race condition where GitHub hasn't created run yet
        max_attempts = 5
        for attempt in range(max_attempts):
            # Query for recent runs with status, conclusion, and createdAt
            # to match newly triggered run
            runs_cmd = [
                "gh",
                "run",
                "list",
                "--workflow",
                workflow,
                "--json",
                "databaseId,status,conclusion,createdAt",
                "--limit",
                "10",
            ]

            runs_result = run_subprocess_with_context(
                runs_cmd,
                operation_context=f"get run ID for workflow '{workflow}'",
                cwd=repo_root,
            )

            # Parse JSON output to extract run ID
            runs_data = json.loads(runs_result.stdout)
            if not runs_data or not isinstance(runs_data, list):
                msg = (
                    "GitHub workflow triggered but could not find run ID. "
                    f"Raw output: {runs_result.stdout[:200]}"
                )
                raise RuntimeError(msg)

            # Find newly triggered run by matching timestamp and filtering skipped/cancelled
            for run in runs_data:
                conclusion = run.get("conclusion")
                if conclusion in ("skipped", "cancelled"):
                    continue

                # Parse the createdAt timestamp
                created_at_str = run.get("createdAt")
                if created_at_str:
                    # GitHub returns ISO 8601 timestamps with 'Z' suffix
                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    # Check if this run was created after our trigger
                    # (with 2-second tolerance for clock skew)
                    if created_at >= trigger_time.replace(microsecond=0) - timedelta(seconds=2):
                        run_id = run["databaseId"]
                        return str(run_id)

            # No valid run found, retry if attempts remaining
            if attempt < max_attempts - 1:
                self._time.sleep(1)

        # All attempts exhausted without finding valid run
        trigger_iso = trigger_time.isoformat()
        msg = (
            f"GitHub workflow triggered but could not find active run ID "
            f"created after {trigger_iso}. "
            "This may indicate GitHub API eventual consistency delay "
            "or all recent runs were skipped/cancelled."
        )
        raise RuntimeError(msg)

    def create_pr(
        self,
        repo_root: Path,
        branch: str,
        title: str,
        body: str,
        base: str | None = None,
    ) -> int:
        """Create a pull request using gh CLI.

        Args:
            repo_root: Repository root directory
            branch: Source branch for the PR
            title: PR title
            body: PR body (markdown)
            base: Target base branch (defaults to repository default branch if None)

        Returns:
            PR number
        """
        cmd = [
            "gh",
            "pr",
            "create",
            "--head",
            branch,
            "--title",
            title,
            "--body",
            body,
        ]

        # Add --base flag if specified
        if base is not None:
            cmd.extend(["--base", base])

        result = run_subprocess_with_context(
            cmd,
            operation_context=f"create pull request for branch '{branch}'",
            cwd=repo_root,
        )

        # Extract PR number from gh output
        # Format: https://github.com/owner/repo/pull/123
        pr_url = result.stdout.strip()
        pr_number = int(pr_url.split("/")[-1])

        return pr_number

    def list_workflow_runs(
        self, repo_root: Path, workflow: str, limit: int = 50
    ) -> list[WorkflowRun]:
        """List workflow runs for a specific workflow.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        try:
            cmd = [
                "gh",
                "run",
                "list",
                "--workflow",
                workflow,
                "--json",
                "databaseId,status,conclusion,headBranch,headSha,displayTitle",
                "--limit",
                str(limit),
            ]

            result = run_subprocess_with_context(
                cmd,
                operation_context=f"list workflow runs for '{workflow}'",
                cwd=repo_root,
            )

            # Parse JSON response
            data = json.loads(result.stdout)

            # Map to WorkflowRun dataclasses
            runs = []
            for run in data:
                workflow_run = WorkflowRun(
                    run_id=str(run["databaseId"]),
                    status=run["status"],
                    conclusion=run.get("conclusion"),
                    branch=run["headBranch"],
                    head_sha=run["headSha"],
                    display_title=run.get("displayTitle"),
                )
                runs.append(workflow_run)

            return runs

        except (RuntimeError, FileNotFoundError, json.JSONDecodeError, KeyError):
            # gh not installed, not authenticated, or JSON parsing failed
            return []

    def get_workflow_run(self, repo_root: Path, run_id: str) -> WorkflowRun | None:
        """Get details for a specific workflow run by ID.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        try:
            cmd = [
                "gh",
                "run",
                "view",
                run_id,
                "--json",
                "databaseId,status,conclusion,headBranch,headSha,displayTitle",
            ]

            result = run_subprocess_with_context(
                cmd,
                operation_context=f"get workflow run details for run {run_id}",
                cwd=repo_root,
            )

            # Parse JSON response
            data = json.loads(result.stdout)

            return WorkflowRun(
                run_id=str(data["databaseId"]),
                status=data["status"],
                conclusion=data.get("conclusion"),
                branch=data["headBranch"],
                head_sha=data["headSha"],
                display_title=data.get("displayTitle"),
            )

        except (RuntimeError, json.JSONDecodeError, KeyError, FileNotFoundError):
            # gh not installed, not authenticated, or command failed (e.g., 404)
            return None

    def get_run_logs(self, repo_root: Path, run_id: str) -> str:
        """Get logs for a workflow run using gh CLI."""
        result = run_subprocess_with_context(
            ["gh", "run", "view", run_id, "--log"],
            operation_context=f"fetch logs for run {run_id}",
            cwd=repo_root,
        )
        return result.stdout

    def get_prs_linked_to_issues(
        self, repo_root: Path, issue_numbers: list[int]
    ) -> dict[int, list[PullRequestInfo]]:
        """Get PRs linked to issues via closing keywords.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        # Early exit for empty input
        if not issue_numbers:
            return {}

        try:
            # Get owner/repo from first PR in repo (needed for GraphQL query)
            # We query for ANY PR to extract owner/repo info
            cmd = ["gh", "pr", "list", "--limit", "1", "--json", "url"]
            stdout = execute_gh_command(cmd, repo_root)
            pr_list = json.loads(stdout)

            # If no PRs exist in repo, return empty dict
            if not pr_list:
                return {}

            # Extract owner/repo from first PR URL
            # Format: https://github.com/owner/repo/pull/123
            pr_url = pr_list[0]["url"]
            parts = pr_url.split("/")
            owner = parts[-4]
            repo = parts[-3]

            # Build and execute GraphQL query to fetch all issues
            query = self._build_issue_pr_linkage_query(issue_numbers, owner, repo)
            response = self._execute_batch_pr_query(query, repo_root)

            # Parse response and build inverse mapping
            return self._parse_issue_pr_linkages(response, owner, repo)

        except (RuntimeError, FileNotFoundError, json.JSONDecodeError, KeyError, IndexError):
            # gh not installed, not authenticated, or parsing failed
            return {}

    def _build_issue_pr_linkage_query(self, issue_numbers: list[int], owner: str, repo: str) -> str:
        """Build GraphQL query to fetch PRs linked to issues.

        Query all PRs in the repository and extract their closingIssuesReferences
        to build the issue-to-PR mapping.

        Args:
            issue_numbers: List of issue numbers to query (used for filtering results)
            owner: Repository owner
            repo: Repository name

        Returns:
            GraphQL query string
        """
        # Query PRs with closingIssuesReferences field
        # We fetch up to 100 PRs at a time - this should cover most repositories
        query = f"""query {{
  repository(owner: "{owner}", name: "{repo}") {{
    pullRequests(
      first: 100,
      states: [OPEN, MERGED, CLOSED],
      orderBy: {{field: CREATED_AT, direction: DESC}}
    ) {{
      nodes {{
        number
        state
        url
        isDraft
        title
        createdAt
        statusCheckRollup {{
          state
        }}
        mergeable
        closingIssuesReferences(first: 100) {{
          nodes {{
            number
          }}
        }}
      }}
    }}
  }}
}}"""
        return query

    def _parse_issue_pr_linkages(
        self, response: dict[str, Any], owner: str, repo: str
    ) -> dict[int, list[PullRequestInfo]]:
        """Parse GraphQL response to extract issue-to-PR mappings.

        Processes PR data with closingIssuesReferences to build the inverse mapping
        from issue numbers to PRs that close them.

        Args:
            response: GraphQL response data
            owner: Repository owner
            repo: Repository name

        Returns:
            Mapping of issue_number -> list of PRs sorted by created_at descending
        """
        # Build inverse mapping: issue_number -> list[(pr_info, created_at)]
        issue_to_prs: dict[int, list[tuple[PullRequestInfo, str]]] = {}

        # Extract repository data
        repo_data = response.get("data", {}).get("repository", {})
        pull_requests = repo_data.get("pullRequests", {})
        pr_nodes = pull_requests.get("nodes", [])

        # Process each PR
        for pr_node in pr_nodes:
            if pr_node is None:
                continue

            # Extract PR fields
            pr_number = pr_node.get("number")
            state = pr_node.get("state")
            url = pr_node.get("url")
            is_draft = pr_node.get("isDraft")
            title = pr_node.get("title")
            created_at = pr_node.get("createdAt")

            # Skip if essential fields are missing
            if pr_number is None or state is None or url is None:
                continue

            # Parse checks status
            checks_passing = None
            status_rollup = pr_node.get("statusCheckRollup")
            if status_rollup is not None:
                rollup_state = status_rollup.get("state")
                if rollup_state == "SUCCESS":
                    checks_passing = True
                elif rollup_state in ("FAILURE", "ERROR"):
                    checks_passing = False

            # Parse conflicts status
            has_conflicts = None
            mergeable = pr_node.get("mergeable")
            if mergeable == "CONFLICTING":
                has_conflicts = True
            elif mergeable == "MERGEABLE":
                has_conflicts = False

            # Create PullRequestInfo
            pr_info = PullRequestInfo(
                number=pr_number,
                state=state,
                url=url,
                is_draft=is_draft if is_draft is not None else False,
                title=title,
                checks_passing=checks_passing,
                owner=owner,
                repo=repo,
                has_conflicts=has_conflicts,
            )

            # Extract linked issues from closingIssuesReferences
            closing_issues = pr_node.get("closingIssuesReferences", {})
            issue_nodes = closing_issues.get("nodes", [])

            for issue_node in issue_nodes:
                if issue_node is None:
                    continue

                issue_number = issue_node.get("number")
                if issue_number is None:
                    continue

                # Add this PR to the issue's list
                if issue_number not in issue_to_prs:
                    issue_to_prs[issue_number] = []

                # Store with timestamp for sorting
                if created_at:
                    issue_to_prs[issue_number].append((pr_info, created_at))

        # Sort PRs for each issue by created_at descending (most recent first)
        result: dict[int, list[PullRequestInfo]] = {}
        for issue_number, prs_with_timestamps in issue_to_prs.items():
            prs_with_timestamps.sort(key=lambda x: x[1], reverse=True)
            result[issue_number] = [pr for pr, _ in prs_with_timestamps]

        return result

    def get_workflow_runs_by_branches(
        self, repo_root: Path, workflow: str, branches: list[str]
    ) -> dict[str, WorkflowRun | None]:
        """Get the most relevant workflow run for each branch.

        Queries GitHub Actions for workflow runs and returns the most relevant
        run for each requested branch. Priority order:
        1. In-progress or queued runs (active runs take precedence)
        2. Failed completed runs (failures are more actionable than successes)
        3. Successful completed runs (most recent)

        Note: Uses list_workflow_runs internally, which already handles gh CLI
        errors gracefully.
        """
        if not branches:
            return {}

        # Get all workflow runs
        all_runs = self.list_workflow_runs(repo_root, workflow, limit=100)

        # Filter to requested branches
        branch_set = set(branches)
        runs_by_branch: dict[str, list[WorkflowRun]] = {}
        for run in all_runs:
            if run.branch in branch_set:
                if run.branch not in runs_by_branch:
                    runs_by_branch[run.branch] = []
                runs_by_branch[run.branch].append(run)

        # Select most relevant run for each branch using priority rules
        result: dict[str, WorkflowRun | None] = {}
        for branch in branches:
            if branch not in runs_by_branch:
                continue

            branch_runs = runs_by_branch[branch]

            # Priority 1: in_progress or queued (active runs)
            active_runs = [r for r in branch_runs if r.status in ("in_progress", "queued")]
            if active_runs:
                result[branch] = active_runs[0]
                continue

            # Priority 2: failed completed runs
            failed_runs = [
                r for r in branch_runs if r.status == "completed" and r.conclusion == "failure"
            ]
            if failed_runs:
                result[branch] = failed_runs[0]
                continue

            # Priority 3: successful completed runs (most recent = first in list)
            completed_runs = [r for r in branch_runs if r.status == "completed"]
            if completed_runs:
                result[branch] = completed_runs[0]
                continue

            # Priority 4: any other runs (unknown status, etc.)
            if branch_runs:
                result[branch] = branch_runs[0]

        return result

    def get_workflow_runs_by_titles(
        self, repo_root: Path, workflow: str, titles: list[str]
    ) -> dict[str, WorkflowRun | None]:
        """Get the most relevant workflow run for each display title.

        Queries GitHub Actions for workflow runs and returns the most relevant
        run for each requested display title. This is useful for workflows
        triggered by issue events where the headBranch is always the default
        branch but the display_title contains the issue title.

        Priority order:
        1. In-progress or queued runs (active runs take precedence)
        2. Failed completed runs (failures are more actionable than successes)
        3. Successful completed runs (most recent)

        Note: Uses list_workflow_runs internally, which already handles gh CLI
        errors gracefully.
        """
        if not titles:
            return {}

        # Get all workflow runs
        all_runs = self.list_workflow_runs(repo_root, workflow, limit=100)

        # Filter to requested titles
        title_set = set(titles)
        runs_by_title: dict[str, list[WorkflowRun]] = {}
        for run in all_runs:
            if run.display_title in title_set:
                if run.display_title not in runs_by_title:
                    runs_by_title[run.display_title] = []
                runs_by_title[run.display_title].append(run)

        # Select most relevant run for each title using priority rules
        result: dict[str, WorkflowRun | None] = {}
        for title in titles:
            if title not in runs_by_title:
                continue

            title_runs = runs_by_title[title]

            # Priority 1: in_progress or queued (active runs)
            active_runs = [r for r in title_runs if r.status in ("in_progress", "queued")]
            if active_runs:
                result[title] = active_runs[0]
                continue

            # Priority 2: failed completed runs
            failed_runs = [
                r for r in title_runs if r.status == "completed" and r.conclusion == "failure"
            ]
            if failed_runs:
                result[title] = failed_runs[0]
                continue

            # Priority 3: successful completed runs (most recent = first in list)
            completed_runs = [r for r in title_runs if r.status == "completed"]
            if completed_runs:
                result[title] = completed_runs[0]
                continue

            # Priority 4: any other runs (unknown status, etc.)
            if title_runs:
                result[title] = title_runs[0]

        return result

    def poll_for_workflow_run(
        self,
        repo_root: Path,
        workflow: str,
        branch_name: str,
        timeout: int = 30,
        poll_interval: int = 2,
    ) -> str | None:
        """Poll for a workflow run matching branch name within timeout.

        Uses multi-factor matching (creation time + event type + branch validation)
        to reliably find the correct workflow run even under high throughput.

        Args:
            repo_root: Repository root directory
            workflow: Workflow filename (e.g., "dispatch-erk-queue.yml")
            branch_name: Expected branch name to match
            timeout: Maximum seconds to poll (default: 30)
            poll_interval: Seconds between poll attempts (default: 2)

        Returns:
            Run ID as string if found within timeout, None otherwise
        """
        start_time = datetime.now(UTC)
        max_attempts = timeout // poll_interval

        for attempt in range(max_attempts):
            # Query for recent runs with branch info
            runs_cmd = [
                "gh",
                "run",
                "list",
                "--workflow",
                workflow,
                "--json",
                "databaseId,status,conclusion,createdAt,event,headBranch",
                "--limit",
                "20",
            ]

            try:
                runs_result = run_subprocess_with_context(
                    runs_cmd,
                    operation_context=(
                        f"poll for workflow run (workflow: {workflow}, branch: {branch_name})"
                    ),
                    cwd=repo_root,
                )

                # Parse JSON output
                runs_data = json.loads(runs_result.stdout)
                if not runs_data or not isinstance(runs_data, list):
                    # No runs found, retry
                    if attempt < max_attempts - 1:
                        self._time.sleep(poll_interval)
                        continue
                    return None

                # Find run matching our criteria
                for run in runs_data:
                    # Skip skipped/cancelled runs
                    conclusion = run.get("conclusion")
                    if conclusion in ("skipped", "cancelled"):
                        continue

                    # Match by branch name
                    head_branch = run.get("headBranch")
                    if head_branch != branch_name:
                        continue

                    # Verify run was created after we started polling (within tolerance)
                    created_at_str = run.get("createdAt")
                    if created_at_str:
                        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                        # Allow 5-second tolerance for runs created just before polling started
                        if created_at >= start_time - timedelta(seconds=5):
                            run_id = run["databaseId"]
                            return str(run_id)

                # No matching run found, retry if attempts remaining
                if attempt < max_attempts - 1:
                    self._time.sleep(poll_interval)

            except (RuntimeError, FileNotFoundError, json.JSONDecodeError):
                # Command failed, retry if attempts remaining
                if attempt < max_attempts - 1:
                    self._time.sleep(poll_interval)
                    continue
                return None

        # Timeout reached without finding matching run
        return None
